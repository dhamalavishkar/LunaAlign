import cv2
import os
import json
import asyncio
import numpy as np
import logging
import sys

from src.matching.classical.feature_matching_pipeline import ClassicalMatchingPipeline
from src.subpixel.subpixel_refinement_pipeline import SubPixelRefinementPipeline
from src.transformation.model_validation_pipeline import ModelValidationPipeline
from src.evaluation.registration_metrics import RegistrationMetrics
from src.explainability.explainability_integration import ExplainabilityPipeline
from src.utils.failure_warning_system import PipelineExhaustionError, assert_minimum_matches
from src.reporting.report_generator import ReportGenerator
from src.data.io.data_loader import DataLoader
from backend.utils.background_tasks import manager

# Import GAP classes from fixed pipeline
try:
    from lunaalign_fixed_pipeline import (
        MultiModalPreprocessor,
        AdaptiveMatcherCascade,
        SpatialDistributionFilter,
        ScientificOutputGenerator,
        TechnicalDecisionLogger,
        QuantitativeBenchmark,
        DependencyChecker,
        FullRegistrationPipeline,
    )
    PIPELINE_AVAILABLE = True
except ImportError as e:
    PIPELINE_AVAILABLE = False
    logging.getLogger(__name__).warning(f"LunaAlign Fixed Pipeline not available: {e}")

logger = logging.getLogger(__name__)

class RegistrationService:
    """
    Orchestrates the entire Mathematical Pipeline in a single shot.
    Now enhanced with GAPs 1-8 from lunaalign_fixed_pipeline.py:
      - GAP 2: Multi-modal OHRC<->TMC2 preprocessing
      - GAP 3: Adaptive matcher cascade (SIFT -> IllumInvariant -> LoFTR)
      - GAP 5: Scientific outputs (uncertainty heatmap, registration overlay)
      - GAP 6: Technical decision logging
      - GAP 7: Spatial distribution enforcement
    """
    @staticmethod
    async def execute_pipeline(session_id: str, mode: str = "standard"):
        logger.info(f"Starting pipeline execution for session {session_id} (mode={mode})")
        session_img_dir = f"backend/cache/images/{session_id}"
        out_dir = f"backend/cache/results/{session_id}"
        os.makedirs(out_dir, exist_ok=True)
        logger.info(f"Output directory for session {session_id}: {out_dir}")

        manifest_path = os.path.join(session_img_dir, "manifest.json")
        src_path = None
        ref_path = None
        src_meta = {}
        ref_meta = {}

        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as mf:
                    manifest = json.load(mf)
                    src_path = manifest.get("source_path")
                    ref_path = manifest.get("reference_path")
                    src_meta = manifest.get("source_metadata", {})
                    ref_meta = manifest.get("reference_metadata", {})
            except Exception as e:
                logger.warning(f"Failed to read manifest: {e}")

        # Fallback search for source and reference files
        if not src_path or not os.path.exists(src_path):
            candidates = [f for f in os.listdir(session_img_dir) if f.startswith("source.") and not f.startswith("source_preview")] if os.path.exists(session_img_dir) else []
            src_path = os.path.join(session_img_dir, candidates[0]) if candidates else os.path.join(session_img_dir, "source.png")

        if not ref_path or not os.path.exists(ref_path):
            candidates = [f for f in os.listdir(session_img_dir) if f.startswith("reference.") and not f.startswith("reference_preview")] if os.path.exists(session_img_dir) else []
            ref_path = os.path.join(session_img_dir, candidates[0]) if candidates else os.path.join(session_img_dir, "reference.png")

        # Load images via DataLoader supporting PDS3 IMG, FITS, TIFF, PNG, etc.
        logger.info(f"Broadcasting raw progress for session {session_id}")
        await manager.broadcast_progress(session_id, "raw", 10)
        loader = DataLoader()
        try:
            src_arr, s_meta = loader.load_image(src_path, max_dim=2048)
            ref_arr, r_meta = loader.load_image(ref_path, max_dim=2048)
            if not src_meta:
                src_meta = s_meta
            if not ref_meta:
                ref_meta = r_meta
        except Exception as load_err:
            logger.error(f"Failed to load images for session {session_id}: {load_err}")
            await manager.broadcast_progress(session_id, "error", 0, {"error": f"Image loading failed: {load_err}"})
            return

        if src_arr is None or ref_arr is None:
            logger.error(f"Corrupted image binaries for session {session_id}")
            await manager.broadcast_progress(session_id, "error", 0, {"error": "Corrupted image binaries"})
            return

        # Ensure 8-bit array for OpenCV
        if src_arr.dtype != np.uint8:
            src_arr = np.clip(src_arr, 0, 255).astype(np.uint8)
        if ref_arr.dtype != np.uint8:
            ref_arr = np.clip(ref_arr, 0, 255).astype(np.uint8)

        # Ensure 3-channel BGR for downstream processing
        if len(src_arr.shape) == 2:
            source = cv2.cvtColor(src_arr, cv2.COLOR_GRAY2BGR)
        else:
            source = src_arr

        if len(ref_arr.shape) == 2:
            ref = cv2.cvtColor(ref_arr, cv2.COLOR_GRAY2BGR)
        else:
            ref = ref_arr

        try:
            # ============================================================
            # ENHANCED PIPELINE with GAPs 2,3,5,6,7 integration
            # ============================================================
            if PIPELINE_AVAILABLE and mode == "multimodal":
                logger.info(f"Using LunaAlign Fixed Pipeline (multimodal) for session {session_id}")
                await manager.broadcast_progress(session_id, "preprocessing", 20)
                await asyncio.sleep(0.1)

                pipeline = FullRegistrationPipeline(
                    mode="multimodal",
                    src_gsd=0.32,
                    ref_gsd=5.0,
                    out_dir=out_dir,
                )

                await manager.broadcast_progress(session_id, "matched", 40)
                await asyncio.sleep(0.1)

                result = pipeline.run(source, ref)

                await manager.broadcast_progress(session_id, "registered", 80)
                await asyncio.sleep(0.1)

                # Map fixed pipeline result to summary.json schema
                H_matrix = result.get("H_matrix")
                n_inliers = result.get("inliers", 0)
                rmse_val = result.get("rmse", "FAILED")

                results = {
                    "model": result.get("model", "N/A"),
                    "rmse": rmse_val,
                    "inliers": n_inliers,
                    "total_matches": result.get("total_matches", 0),
                    "filtered_matches": result.get("filtered_matches", 0),
                    "H_matrix": H_matrix,
                    "dossier_index": 0,
                    "status": "SUCCESS" if H_matrix is not None else "DEGRADED",
                    "matcher_used": result.get("matcher_used", "unknown"),
                    "spatial_distribution": result.get("spatial_distribution", {}),
                    "scale_ratio_applied": result.get("scale_ratio_applied", 1.0),
                    "outputs": result.get("outputs", {}),
                    "mode": "multimodal",
                }

                with open(os.path.join(out_dir, "summary.json"), "w") as f:
                    json.dump(results, f)

                try:
                    ReportGenerator.generate(session_id, results)
                except Exception as rg_err:
                    logger.warning(f"Report generation failed: {rg_err}")

                await manager.broadcast_progress(session_id, "complete", 100, results)
                logger.info(f"Multimodal pipeline completed for session {session_id}")
                return

            # ============================================================
            # STANDARD PIPELINE (enhanced with GAP 3 adaptive cascade)
            # ============================================================
            # 1. Matching
            logger.info(f"Broadcasting matched progress for session {session_id}")
            await manager.broadcast_progress(session_id, "matched", 30)
            await asyncio.sleep(0.1)

            kp1, kp2, matches = None, None, []

            # Try adaptive cascade first if available
            if PIPELINE_AVAILABLE:
                logger.info(f"Using AdaptiveMatcherCascade for session {session_id}")
                try:
                    src_gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY) if len(source.shape) == 3 else source
                    ref_gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY) if len(ref.shape) == 3 else ref
                    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
                    src_proc = clahe.apply(src_gray)
                    ref_proc = clahe.apply(ref_gray)
                    loftr_ok = DependencyChecker.loftr_available()
                    cascade = AdaptiveMatcherCascade(loftr_ok)
                    kp1, kp2, matches, matcher_used = cascade.run(src_proc, ref_proc)
                    logger.info(f"AdaptiveMatcherCascade: {len(matches)} matches via {matcher_used}")
                except Exception as cascade_err:
                    logger.warning(f"Cascade failed, falling back to classical: {cascade_err}")
                    kp1, kp2, matches = None, None, []

            # Fallback to classical SIFT if cascade didn't produce enough
            if kp1 is None or len(matches) < 4:
                logger.info(f"Running classical matching for session {session_id}")
                pipe = ClassicalMatchingPipeline('SIFT')
                kp1, kp2, matches = pipe.run_matching(source, ref)
                logger.info(f"Found {len(matches)} matches for session {session_id}")

            # Fallback to multi-scale
            if len(matches) < 4:
                logger.info(f"Matches < 4 ({len(matches)}), attempting Multi-Scale ScaleSpaceMatcher fallback...")
                try:
                    from src.multiscale.scale_space_matcher import ScaleSpaceMatcher
                    scale_matcher = ScaleSpaceMatcher(matcher_algo='SIFT', levels=3)
                    ms_kp1, ms_kp2, ms_matches = scale_matcher.match_coarse_to_fine(source, ref)
                    if len(ms_matches) >= 4:
                        kp1, kp2, matches = ms_kp1, ms_kp2, ms_matches
                        logger.info(f"ScaleSpaceMatcher succeeded with {len(matches)} matches")
                except Exception as ms_err:
                    logger.warning(f"ScaleSpaceMatcher fallback attempted but failed: {ms_err}")

            if len(matches) < 4:
                err_msg = f"Not enough matches to compute geometric transformation ({len(matches)} found, minimum 4 required)."
                logger.warning(f"Pipeline exhaustion for session {session_id}: {err_msg}")
                
                failure_results = {
                    "model": "N/A",
                    "rmse": "FAILED",
                    "inliers": 0,
                    "total_matches": len(matches),
                    "H_matrix": None,
                    "dossier_index": -1,
                    "status": "INSUFFICIENT_MATCHES",
                    "error": err_msg,
                    "diagnostic_report": {
                        "incident": "Extreme Multi-Modal Scale Differential (e.g. OHRC 0.25m/px vs TMC-2 5.0m/px)",
                        "cause": "Scale variance (20x) exceeds classical SIFT octave limits.",
                        "remediation": "Try multimodal mode or use Deep Learning Semantic Matcher (LoFTR)."
                    }
                }
                with open(os.path.join(out_dir, "summary.json"), "w") as f:
                    json.dump(failure_results, f)
                    
                await manager.broadcast_progress(session_id, "complete", 100, failure_results)
                logger.info(f"Exhaustion summary recorded for session {session_id}")
                return

            # GAP 7: Spatial Distribution Enforcement
            if PIPELINE_AVAILABLE:
                try:
                    spatial_filter = SpatialDistributionFilter()
                    ref_gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY) if len(ref.shape) == 3 else ref
                    filtered_matches, dist_metrics = spatial_filter.filter(
                        kp1, kp2, matches, ref_gray.shape
                    )
                    if len(filtered_matches) >= 4:
                        matches = filtered_matches
                        logger.info(f"Spatial filter: {dist_metrics}")
                except Exception as sf_err:
                    logger.warning(f"Spatial distribution filter failed: {sf_err}")

            # 2. Refinement
            logger.info(f"Broadcasting verified progress for session {session_id}")
            await manager.broadcast_progress(session_id, "verified", 60)
            await asyncio.sleep(0.1)
            logger.info(f"Running refinement for session {session_id}")
            refiner = SubPixelRefinementPipeline()
            r_kp1, r_kp2, r_matches = refiner.refine_matches(source, ref, kp1, kp2, matches)
            logger.info(f"Refinement complete for session {session_id}")

            # 3. Model Selection
            logger.info(f"Broadcasting registered progress for session {session_id}")
            await manager.broadcast_progress(session_id, "registered", 80)
            await asyncio.sleep(0.1)
            logger.info(f"Running model validation for session {session_id}")
            val = ModelValidationPipeline()
            model_name, H, inlier_mask, rmse = val.select_transformation(r_kp1, r_kp2, r_matches)
            logger.info(f"Model validation complete for session {session_id}: {model_name}")

            # 4. Explainability Dumping
            logger.info(f"Broadcasting generating_dossiers progress for session {session_id}")
            await manager.broadcast_progress(session_id, "generating_dossiers", 90)
            await asyncio.sleep(0.1)
            explainer = ExplainabilityPipeline(output_dir=out_dir)

            dossier_idx = -1
            inliers_count = 0
            if inlier_mask is not None:
                for i, mask_val in enumerate(inlier_mask):
                    if mask_val[0] == 1:
                        dossier_idx = i
                        inliers_count += 1
                        break

                if dossier_idx != -1:
                    logger.info(f"Generating dossier for index {dossier_idx} for session {session_id}")
                    explainer.generate_dossier(source, ref, kp1, kp2, matches, dossier_idx, H, r_kp1, r_kp2)

            # GAP 5: Generate scientific outputs (uncertainty heatmap + overlay)
            if PIPELINE_AVAILABLE and H is not None:
                try:
                    sci_gen = ScientificOutputGenerator(out_dir)
                    src_gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY) if len(source.shape) == 3 else source
                    ref_gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY) if len(ref.shape) == 3 else ref
                    sci_gen.generate_uncertainty_heatmap(src_gray, kp1, matches, inlier_mask)
                    sci_gen.generate_registration_overlay(src_gray, ref_gray, H)
                    logger.info(f"Scientific outputs generated for session {session_id}")
                except Exception as sci_err:
                    logger.warning(f"Scientific output generation failed: {sci_err}")

            # Calculate actual metric
            if H is not None:
                inlier_pts1 = []
                inlier_pts2 = []
                for m, inlier in zip(r_matches, inlier_mask):
                    if inlier[0] == 1:
                        inlier_pts1.append(r_kp1[m.queryIdx].pt)
                        inlier_pts2.append(r_kp2[m.trainIdx].pt)

                pts1 = np.float32(inlier_pts1).reshape(-1, 2)
                pts2 = np.float32(inlier_pts2).reshape(-1, 2)
                final_rmse = RegistrationMetrics.compute_rmse(pts1, pts2, H)
                logger.info(f"Final RMSE for session {session_id}: {final_rmse}")
            else:
                final_rmse = -1
                logger.warning(f"No homography found for session {session_id}")

            # Write Final Results JSON
            results = {
                "model": model_name,
                "rmse": round(float(final_rmse), 4) if final_rmse != -1 else "FAILED",
                "inliers": inliers_count,
                "total_matches": len(r_matches),
                "H_matrix": H.tolist() if H is not None else None,
                "dossier_index": dossier_idx,
                "status": "SUCCESS" if H is not None else "DEGRADED",
                "mode": mode,
                "source_metadata": src_meta,
                "reference_metadata": ref_meta,
            }

            logger.info(f"Writing results for session {session_id}: {results}")

            with open(os.path.join(out_dir, "summary.json"), "w") as f:
                json.dump(results, f)

            # Generate the scientific report autonomously
            logger.info(f"Generating scientific report for session {session_id}")
            ReportGenerator.generate(session_id, results)

            # GAP 6: Write technical decisions log
            if PIPELINE_AVAILABLE:
                try:
                    tech_log = TechnicalDecisionLogger()
                    tech_log.record(
                        "Pipeline mode selection",
                        f"Standard mode used for session {session_id}. "
                        "For OHRC vs TMC2 cross-sensor pairs, use multimodal mode.",
                        "Multimodal mode (for 20x scale differential)"
                    )
                    tech_log.write()
                except Exception:
                    pass

            logger.info(f"Broadcasting complete progress for session {session_id}")
            await manager.broadcast_progress(session_id, "complete", 100, results)
            logger.info(f"Pipeline execution completed for session {session_id}")

        except PipelineExhaustionError as e:
            logger.error(f"PipelineExhaustionError for session {session_id}: {e}")
            failure_results = {
                "model": "N/A",
                "rmse": "FAILED",
                "inliers": 0,
                "total_matches": 0,
                "H_matrix": None,
                "dossier_index": -1,
                "status": "EXHAUSTION",
                "error": str(e)
            }
            with open(os.path.join(out_dir, "summary.json"), "w") as f:
                json.dump(failure_results, f)
            await manager.broadcast_progress(session_id, "complete", 100, failure_results)
        except Exception as e:
            logger.error(f"Unexpected error in pipeline for session {session_id}: {e}", exc_info=True)
            await manager.broadcast_progress(session_id, "error", 0, {"error": str(e)})

    @staticmethod
    async def run_benchmark(session_id: str):
        """GAP 4: Run quantitative benchmark comparing all matchers."""
        if not PIPELINE_AVAILABLE:
            return {"error": "Pipeline not available"}

        src_path = f"backend/cache/images/{session_id}/source.png"
        ref_path = f"backend/cache/images/{session_id}/reference.png"
        out_dir = f"backend/cache/results/{session_id}"

        source = cv2.imread(src_path)
        ref = cv2.imread(ref_path)

        if source is None or ref is None:
            return {"error": "Images not found"}

        src_gray = cv2.cvtColor(source, cv2.COLOR_BGR2GRAY) if len(source.shape) == 3 else source
        ref_gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY) if len(ref.shape) == 3 else ref

        loftr_ok = DependencyChecker.loftr_available()
        bm = QuantitativeBenchmark(loftr_ok)
        bm_results = bm.run(src_gray, ref_gray)

        # Save to file
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "benchmark.json"), "w") as f:
            json.dump(bm_results, f, indent=2, default=str)

        # Append to experiment log
        QuantitativeBenchmark.append_to_experiment_log(
            bm_results,
            log_path="EXPERIMENT_LOG.md",
        )

        return bm_results
