import cv2
import os
import json
import asyncio
import numpy as np
import logging

from src.matching.classical.feature_matching_pipeline import ClassicalMatchingPipeline
from src.subpixel.subpixel_refinement_pipeline import SubPixelRefinementPipeline
from src.transformation.model_validation_pipeline import ModelValidationPipeline
from src.evaluation.registration_metrics import RegistrationMetrics
from src.explainability.explainability_integration import ExplainabilityPipeline
from src.utils.failure_warning_system import PipelineExhaustionError, assert_minimum_matches
from src.reporting.report_generator import ReportGenerator
from backend.utils.background_tasks import manager

logger = logging.getLogger(__name__)

class RegistrationService:
    """
    Orchestrates the entire Mathematical Pipeline in a single shot.
    Receives paths to cached images, executes the pipeline asynchronously, 
    and broadcasts state transitions via the WebSocket manager.
    """
    @staticmethod
    async def execute_pipeline(session_id: str):
        logger.info(f"Starting pipeline execution for session {session_id}")
        src_path = f"backend/cache/images/{session_id}/source.png"
        ref_path = f"backend/cache/images/{session_id}/reference.png"
        out_dir = f"backend/cache/results/{session_id}"
        os.makedirs(out_dir, exist_ok=True)
        logger.info(f"Output directory for session {session_id}: {out_dir}")

        # Brief yield to allow the frontend WebSocket handshake to establish
        await asyncio.sleep(0.3)

        # Load images
        logger.info(f"Broadcasting raw progress for session {session_id}")
        await manager.broadcast_progress(session_id, "raw", 10)
        source = cv2.imread(src_path)
        ref = cv2.imread(ref_path)

        if source is None or ref is None:
            logger.error(f"Corrupted image binaries for session {session_id}")
            await manager.broadcast_progress(session_id, "error", 0, {"error": "Corrupted image binaries"})
            return

        try:
            # 1. Matching
            logger.info(f"Broadcasting matched progress for session {session_id}")
            await manager.broadcast_progress(session_id, "matched", 30)
            await asyncio.sleep(0.1) # Yield to event loop for WS flush
            logger.info(f"Running classical matching for session {session_id}")
            pipe = ClassicalMatchingPipeline('SIFT')
            kp1, kp2, matches = pipe.run_matching(source, ref)
            logger.info(f"Found {len(matches)} matches for session {session_id}")

            # Fallback to multi-scale coarse-to-fine matcher if SIFT matches are low
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
                # Documented in Required.md: Extreme multi-modal case (OHRC vs TMC2)
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
                        "cause": "Scale variance (20x) exceeds classical SIFT octave limits. Inverted crater shadow topologies shattered local gradient histogram KNN dependencies.",
                        "remediation": "Requires Deep Learning Semantic Matcher (LoFTR) or coarse orbit ephemeris pre-alignment."
                    }
                }
                with open(os.path.join(out_dir, "summary.json"), "w") as f:
                    json.dump(failure_results, f)
                    
                await manager.broadcast_progress(session_id, "complete", 100, failure_results)
                logger.info(f"Exhaustion summary recorded for session {session_id}")
                return

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

            # We'll just generate a dossier for the first inlier match for speed
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

            # Calculate actual metric
            if H is not None:
                # Filter to just inliers
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
                "status": "SUCCESS" if H is not None else "DEGRADED"
            }

            logger.info(f"Writing results for session {session_id}: {results}")

            with open(os.path.join(out_dir, "summary.json"), "w") as f:
                json.dump(results, f)

            # Generate the scientific report autonomously
            logger.info(f"Generating scientific report for session {session_id}")
            ReportGenerator.generate(session_id, results)

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
