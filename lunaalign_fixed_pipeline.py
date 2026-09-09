"""
LunaAlign AI — Fixed Registration Pipeline

SIH26166 | ISRO Problem Statement

============================================================

This file addresses all 8 judging gaps identified by the panel:



  GAP 1  → Real data acquisition helper (ISRO PRADAN + LROC PDS)

  GAP 2  → Multi-modal OHRC↔TMC2 registration (cross-sensor, 20× scale)

  GAP 3  → Adaptive matcher cascade: SIFT → IlluminationInvariant → LoFTR

  GAP 4  → Quantitative benchmark runner with RMSE/TRE table

  GAP 5  → GUI-ready scientific outputs: uncertainty heatmap + batch mode

  GAP 6  → Technical decision log (auto-written at runtime)

  GAP 7  → Spatial distribution enforcement wired into live pipeline

  GAP 8  → Reproducibility: dependency check + graceful fallbacks



Usage:

  python lunaalign_fixed_pipeline.py --source path/to/ohrc.png \

                                     --reference path/to/tmc2.png \

                                     --mode multimodal \

                                     --benchmark

"""



import cv2

import json

import os

import sys

import time

import logging

import argparse

import numpy as np

from pathlib import Path

from typing import Tuple, List, Dict, Any, Optional



logging.basicConfig(

    level=logging.INFO,

    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s"

)

logger = logging.getLogger("LunaAlign")





# ============================================================

# GAP 8 — REPRODUCIBILITY: Dependency check with graceful fallbacks

# ============================================================



class DependencyChecker:

    """

    Verifies runtime dependencies and records which matchers are available.

    Prevents silent failures (previously: LoFTR guarded by try/except and

    never actually loaded).

    """



    REQUIRED = ["cv2", "numpy"]

    OPTIONAL = {

        "torch": "PyTorch (required for LoFTR deep matcher)",

        "kornia": "Kornia (required for LoFTR deep matcher)",

    }



    @classmethod

    def check(cls) -> Dict[str, bool]:

        status = {}

        for pkg in cls.REQUIRED:

            try:

                __import__(pkg)

                status[pkg] = True

            except ImportError:

                logger.error(f"REQUIRED package missing: {pkg}. Install via pip.")

                status[pkg] = False



        for pkg, desc in cls.OPTIONAL.items():

            try:

                __import__(pkg)

                status[pkg] = True

                logger.info(f"✓ Optional dep available: {pkg} ({desc})")

            except ImportError:

                status[pkg] = False

                logger.warning(f"✗ Optional dep MISSING: {pkg} ({desc}). "

                               f"Falling back to classical matchers.")

        return status



    @classmethod

    def loftr_available(cls) -> bool:

        deps = cls.check()

        return deps.get("torch", False) and deps.get("kornia", False)





DEPS = DependencyChecker.check()





# ============================================================

# GAP 1 — REAL DATA ACQUISITION HELPER

# ============================================================



class RealDataAcquisition:

    """

    Provides URLs and metadata to download real Chandrayaan-2 images.

    The project's DATASET_STATE shows 0 real images. This class gives

    the team concrete download targets for the demo.



    Usage:

        RealDataAcquisition.print_download_guide()

        img = RealDataAcquisition.load_or_create_proxy("ohrc_tile.png", sensor="OHRC")

    """



    SOURCES = {

        "OHRC": {

            "portal": "https://pradan.issdc.gov.in/ch2/protected/payload.xhtml",

            "product_id_example": "ch2_ohr_ncp_20221015T074521591_d_img",

            "gsd_m": 0.32,

            "description": "High-resolution 0.32 m/px nadir panchromatic"

        },

        "TMC2": {

            "portal": "https://pradan.issdc.gov.in/ch2/protected/payload.xhtml",

            "product_id_example": "ch2_tmc_20221015T074521591_d_img",

            "gsd_m": 5.0,

            "description": "Medium-resolution 5 m/px stereo triplet"

        },

        "LROC_NAC": {

            "portal": "https://pds.lroc.asu.edu/data/LRO-L-LROC-2-EDR-V1.0/",

            "product_id_example": "M1316828209LE",

            "gsd_m": 0.5,

            "description": "NASA LRO NAC 0.5 m/px — free, no login required"

        }

    }



    @classmethod

    def print_download_guide(cls):

        print("\n" + "="*60)

        print("REAL DATA ACQUISITION GUIDE — LunaAlign SIH26166")

        print("="*60)

        for sensor, info in cls.SOURCES.items():

            print(f"\n{sensor}  ({info['gsd_m']} m/px)")

            print(f"  Portal : {info['portal']}")

            print(f"  Example: {info['product_id_example']}")

            print(f"  Notes  : {info['description']}")

        print("\nRecommended for demo: Download one LROC NAC pair "

              "(no login) + one OHRC tile from PRADAN for cross-sensor test.")

        print("="*60 + "\n")



    @classmethod

    def load_or_create_proxy(cls, path: str, sensor: str = "OHRC") -> np.ndarray:

        """

        Loads a real image if it exists; otherwise synthesises a realistic

        lunar proxy so the pipeline always has something to run on.

        """

        if os.path.exists(path):

            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)

            if img is not None:

                logger.info(f"Loaded real image: {path} ({img.shape})")

                return img

            logger.warning(f"File exists but could not be read: {path}")



        logger.warning(f"Real image not found at '{path}'. "

                       f"Generating synthetic lunar proxy for sensor={sensor}.")

        return cls._generate_lunar_proxy(sensor)



    @classmethod

    def _generate_lunar_proxy(cls, sensor: str = "OHRC") -> np.ndarray:

        """

        Generates a synthetic grayscale lunar surface with craters, ridges,

        and realistic noise. Different GSD for OHRC vs TMC2.

        """

        np.random.seed(42)

        h, w = (512, 512) if sensor == "OHRC" else (128, 128)  # 20× area ratio

        base = np.random.normal(128, 20, (h, w)).clip(0, 255).astype(np.uint8)



        # Add gaussian blur for terrain smoothness

        base = cv2.GaussianBlur(base, (15, 15), 5)



        # Stamp craters

        n_craters = 12 if sensor == "OHRC" else 4

        for _ in range(n_craters):

            cx, cy = np.random.randint(40, w - 40), np.random.randint(40, h - 40)

            r = np.random.randint(8, 30)

            cv2.circle(base, (cx, cy), r, int(np.random.uniform(50, 90)), -1)

            cv2.circle(base, (cx, cy), r + 3, int(np.random.uniform(160, 200)), 3)



        # Add ridgelines

        for _ in range(3):

            pt1 = (np.random.randint(0, w), np.random.randint(0, h))

            pt2 = (np.random.randint(0, w), np.random.randint(0, h))

            cv2.line(base, pt1, pt2, int(np.random.uniform(150, 200)), 2)



        # Sensor noise

        noise_std = 8 if sensor == "OHRC" else 15

        noise = np.random.normal(0, noise_std, base.shape)

        base = np.clip(base.astype(np.float32) + noise, 0, 255).astype(np.uint8)

        return base





# ============================================================

# GAP 2 — MULTI-MODAL REGISTRATION (OHRC ↔ TMC2, 20× scale gap)

# ============================================================



class MultiModalPreprocessor:

    """

    Bridges the gap between OHRC (0.32 m/px) and TMC2 (5 m/px) imagery.

    Previously: MultiModalAdapter only did histogram matching, which is

    insufficient for the 20× resolution difference.



    Fix:

      1. Downsample OHRC to match TMC2 GSD before feature matching.

      2. Histogram match to normalise illumination difference.

      3. Upscale matched keypoints back to OHRC coordinate space.

    """



    def __init__(self, src_gsd: float = 0.32, ref_gsd: float = 5.0):

        self.src_gsd = src_gsd

        self.ref_gsd = ref_gsd

        self.scale_ratio = ref_gsd / src_gsd  # ≈ 15.6 for OHRC→TMC2



    def preprocess(

        self, src: np.ndarray, ref: np.ndarray

    ) -> Tuple[np.ndarray, np.ndarray, float]:

        """

        Returns: (preprocessed_src, preprocessed_ref, scale_ratio_applied)

        scale_ratio_applied is needed to map keypoints back to original coords.

        """

        src_gray = self._to_gray(src)

        ref_gray = self._to_gray(ref)



        # Step 1: Downsample source to approximately match reference GSD

        if self.scale_ratio > 1.5:

            new_w = max(32, int(src_gray.shape[1] / self.scale_ratio))

            new_h = max(32, int(src_gray.shape[0] / self.scale_ratio))

            src_gray = cv2.resize(

                src_gray, (new_w, new_h), interpolation=cv2.INTER_AREA

            )

            logger.info(

                f"MultiModal: Downsampled source from original to "

                f"{src_gray.shape} (scale ratio {self.scale_ratio:.1f}×)"

            )

        else:

            logger.info("MultiModal: Scale ratio < 1.5, skipping downsample.")



        # Step 2: CLAHE to boost local contrast (critical for low-texture lunar)

        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))

        src_gray = clahe.apply(src_gray)

        ref_gray = clahe.apply(ref_gray)



        # Step 3: Histogram matching to bridge modality gap

        src_adapted = self._histogram_match(src_gray, ref_gray)



        return src_adapted, ref_gray, self.scale_ratio



    def scale_keypoints_back(

        self, kp: List[cv2.KeyPoint], scale: float

    ) -> List[cv2.KeyPoint]:

        """Rescales keypoint coordinates from downsampled space → original."""

        return [

            cv2.KeyPoint(

                x=kp_.pt[0] * scale,

                y=kp_.pt[1] * scale,

                size=kp_.size * scale,

                angle=kp_.angle,

                response=kp_.response,

                octave=kp_.octave,

                class_id=kp_.class_id,

            )

            for kp_ in kp

        ]



    @staticmethod

    def _to_gray(img: np.ndarray) -> np.ndarray:

        if len(img.shape) == 3:

            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        return img.copy()



    @staticmethod

    def _histogram_match(src: np.ndarray, ref: np.ndarray) -> np.ndarray:

        src_hist, _ = np.histogram(src.flatten(), 256, [0, 256])

        ref_hist, _ = np.histogram(ref.flatten(), 256, [0, 256])

        src_cdf = (src_hist.cumsum() / src_hist.cumsum().max())

        ref_cdf = (ref_hist.cumsum() / ref_hist.cumsum().max())

        lut = np.array([

            np.argmin(np.abs(ref_cdf - src_cdf[i])) for i in range(256)

        ], dtype=np.uint8)

        return cv2.LUT(src, lut)





# ============================================================

# GAP 3 — ADAPTIVE MATCHER CASCADE (SIFT → IllumInvariant → LoFTR)

# ============================================================



class AdaptiveMatcherCascade:

    """

    The live registration_service.py only ever calls ClassicalMatchingPipeline('SIFT').

    LoFTR and IlluminationInvariantMatcher are written but never wired in.



    This cascade tries matchers in order of increasing power:

      Stage 1: SIFT (fast, works for same-sensor pairs)

      Stage 2: IlluminationInvariant + PhaseCongruency (handles lighting change)

      Stage 3: LoFTR  (deep, handles large appearance gap — OHRC vs TMC2)



    It stops at the first stage that produces ≥ MIN_INLIERS inliers.

    """



    MIN_INLIERS = 8          # Minimum to trust a match result

    RANSAC_THRESH = 4.0      # Reprojection threshold in pixels



    def __init__(self, loftr_available: bool = False):

        self.loftr_ok = loftr_available



    def run(

        self,

        src: np.ndarray,

        ref: np.ndarray

    ) -> Tuple[List[cv2.KeyPoint], List[cv2.KeyPoint], List[cv2.DMatch], str]:

        """

        Returns (kp1, kp2, matches, matcher_name_used).

        Falls through the cascade until sufficient inliers are found.

        """

        results = []



        # ── Stage 1: SIFT ─────────────────────────────────────────

        kp1, kp2, matches = self._sift_match(src, ref)

        n_inliers, _ = self._count_inliers(kp1, kp2, matches)

        logger.info(f"  [SIFT]              matches={len(matches)}, inliers={n_inliers}")

        results.append(("SIFT", kp1, kp2, matches, n_inliers))



        if n_inliers >= self.MIN_INLIERS:

            logger.info("  → SIFT sufficient. Cascade stops at Stage 1.")

            return kp1, kp2, matches, "SIFT"



        # ── Stage 2: Illumination-Invariant (Phase Congruency) ────

        logger.info("  SIFT insufficient. Trying IlluminationInvariant (Phase Congruency)...")

        kp1, kp2, matches = self._illumination_invariant_match(src, ref)

        n_inliers, _ = self._count_inliers(kp1, kp2, matches)

        logger.info(f"  [IllumInvariant]    matches={len(matches)}, inliers={n_inliers}")

        results.append(("IlluminationInvariant", kp1, kp2, matches, n_inliers))



        if n_inliers >= self.MIN_INLIERS:

            logger.info("  → IllumInvariant sufficient. Cascade stops at Stage 2.")

            return kp1, kp2, matches, "IlluminationInvariant"



        # ── Stage 3: LoFTR (deep, if available) ──────────────────

        if self.loftr_ok:

            logger.info("  IllumInvariant insufficient. Trying LoFTR...")

            kp1, kp2, matches = self._loftr_match(src, ref)

            n_inliers, _ = self._count_inliers(kp1, kp2, matches)

            logger.info(f"  [LoFTR]             matches={len(matches)}, inliers={n_inliers}")

            results.append(("LoFTR", kp1, kp2, matches, n_inliers))



            if n_inliers >= self.MIN_INLIERS:

                logger.info("  → LoFTR sufficient. Cascade stops at Stage 3.")

                return kp1, kp2, matches, "LoFTR"

        else:

            logger.warning("  LoFTR unavailable (torch/kornia not installed). "

                           "Install: pip install torch torchvision kornia")



        # Return best stage even if below threshold

        best = max(results, key=lambda x: x[4])

        logger.warning(

            f"  All stages below MIN_INLIERS={self.MIN_INLIERS}. "

            f"Best was {best[0]} with {best[4]} inliers."

        )

        return best[1], best[2], best[3], best[0] + "_BEST_EFFORT"



    # ── Internal matcher implementations ─────────────────────────



    def _sift_match(

        self, src: np.ndarray, ref: np.ndarray

    ) -> Tuple[List[cv2.KeyPoint], List[cv2.KeyPoint], List[cv2.DMatch]]:

        gray1 = self._gray(src)

        gray2 = self._gray(ref)

        sift = cv2.SIFT_create(nfeatures=2000, contrastThreshold=0.02)

        kp1, des1 = sift.detectAndCompute(gray1, None)

        kp2, des2 = sift.detectAndCompute(gray2, None)

        if des1 is None or des2 is None or len(kp1) < 2 or len(kp2) < 2:

            return [], [], []

        flann = cv2.FlannBasedMatcher(

            {"algorithm": 1, "trees": 5}, {"checks": 50}

        )

        raw = flann.knnMatch(des1, des2, k=2)

        good = [m for m, n in raw if m.distance < 0.75 * n.distance]

        return kp1, kp2, good



    def _illumination_invariant_match(

        self, src: np.ndarray, ref: np.ndarray

    ) -> Tuple[List[cv2.KeyPoint], List[cv2.KeyPoint], List[cv2.DMatch]]:

        """

        Phase-congruency structural transform, then SIFT on transformed images.

        PhaseCongruency is illumination-invariant because it responds to

        discontinuities in local phase, not pixel intensity magnitude.

        """

        gray1 = self._gray(src).astype(np.float32) / 255.0

        gray2 = self._gray(ref).astype(np.float32) / 255.0



        struct1 = self._phase_congruency(gray1)

        struct2 = self._phase_congruency(gray2)



        # Convert structural maps back to uint8 for SIFT

        s1_u8 = (struct1 * 255).clip(0, 255).astype(np.uint8)

        s2_u8 = (struct2 * 255).clip(0, 255).astype(np.uint8)



        sift = cv2.SIFT_create(nfeatures=2000, contrastThreshold=0.01)

        kp1, des1 = sift.detectAndCompute(s1_u8, None)

        kp2, des2 = sift.detectAndCompute(s2_u8, None)



        if des1 is None or des2 is None or len(kp1) < 2 or len(kp2) < 2:

            return [], [], []



        bf = cv2.BFMatcher(cv2.NORM_L2)

        raw = bf.knnMatch(des1, des2, k=2)

        good = [m for m, n in raw if m.distance < 0.80 * n.distance]

        return kp1, kp2, good



    def _loftr_match(

        self, src: np.ndarray, ref: np.ndarray

    ) -> Tuple[List[cv2.KeyPoint], List[cv2.KeyPoint], List[cv2.DMatch]]:

        """

        LoFTR deep matcher. Requires torch + kornia.

        Produces semi-dense matches — handles low-texture lunar terrain

        where SIFT finds zero repeatable keypoints.

        """

        import torch

        import kornia.feature as kf



        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        matcher = kf.LoFTR(pretrained="outdoor").to(device).eval()



        gray1 = self._gray(src)

        gray2 = self._gray(ref)



        # LoFTR requires input size divisible by 8

        h1, w1 = gray1.shape

        h2, w2 = gray2.shape

        gray1 = cv2.resize(gray1, (w1 - w1 % 8, h1 - h1 % 8))

        gray2 = cv2.resize(gray2, (w2 - w2 % 8, h2 - h2 % 8))



        t1 = torch.from_numpy(gray1)[None, None].float().to(device) / 255.0

        t2 = torch.from_numpy(gray2)[None, None].float().to(device) / 255.0



        with torch.no_grad():

            corr = matcher({"image0": t1, "image1": t2})



        mkpts0 = corr["keypoints0"].cpu().numpy()

        mkpts1 = corr["keypoints1"].cpu().numpy()

        conf = corr["confidence"].cpu().numpy()



        conf_thresh = 0.2

        mask = conf > conf_thresh

        mkpts0, mkpts1, conf = mkpts0[mask], mkpts1[mask], conf[mask]



        kp1, kp2, matches = [], [], []

        for i, (p0, p1, c) in enumerate(zip(mkpts0, mkpts1, conf)):

            kp1.append(cv2.KeyPoint(float(p0[0]), float(p0[1]), 1.0))

            kp2.append(cv2.KeyPoint(float(p1[0]), float(p1[1]), 1.0))

            matches.append(cv2.DMatch(i, i, 1.0 - float(c)))



        return kp1, kp2, matches



    def _count_inliers(

        self,

        kp1: List[cv2.KeyPoint],

        kp2: List[cv2.KeyPoint],

        matches: List[cv2.DMatch],

    ) -> Tuple[int, Optional[np.ndarray]]:

        if len(matches) < 4:

            return 0, None

        pts1 = np.float32([kp1[m.queryIdx].pt for m in matches])

        pts2 = np.float32([kp2[m.trainIdx].pt for m in matches])

        _, mask = cv2.findHomography(

            pts1, pts2, cv2.RANSAC, self.RANSAC_THRESH

        )

        if mask is None:

            return 0, None

        return int(mask.sum()), mask



    @staticmethod

    def _gray(img: np.ndarray) -> np.ndarray:

        if len(img.shape) == 3:

            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        return img.copy()



    @staticmethod

    def _phase_congruency(gray_f32: np.ndarray) -> np.ndarray:

        """

        Lightweight phase congruency approximation using log-Gabor filters.

        Returns an edge/structure map that is invariant to linear illumination.

        """

        # Use 4 orientations, 4 scales of log-Gabor

        pc = np.zeros_like(gray_f32)

        for theta in np.linspace(0, np.pi, 4, endpoint=False):

            for sigma in [2, 4, 8, 16]:

                kernel = AdaptiveMatcherCascade._log_gabor_kernel(

                    gray_f32.shape, sigma, theta

                )

                filtered = np.real(

                    np.fft.ifft2(np.fft.fft2(gray_f32) * kernel)

                )

                pc += np.abs(filtered)

        # Normalise

        pc -= pc.min()

        if pc.max() > 0:

            pc /= pc.max()

        return pc



    @staticmethod

    def _log_gabor_kernel(

        shape: Tuple[int, int], sigma: float, theta: float

    ) -> np.ndarray:

        rows, cols = shape

        y, x = np.mgrid[-rows // 2:rows // 2, -cols // 2:cols // 2]

        # Rotate

        x_theta = x * np.cos(theta) + y * np.sin(theta)

        y_theta = -x * np.sin(theta) + y * np.cos(theta)

        # Log-Gabor in frequency domain

        r = np.sqrt(x_theta ** 2 + (y_theta / (sigma * 0.5 + 1e-6)) ** 2) + 1e-6

        kernel = np.exp(-(np.log(r / (sigma + 1e-6)) ** 2) / (2 * 0.55 ** 2))

        return np.fft.ifftshift(kernel)





# ============================================================

# GAP 7 — SPATIAL DISTRIBUTION ENFORCEMENT (wired into live pipeline)

# ============================================================



class SpatialDistributionFilter:

    """

    Previously: UniformDistributionPipeline existed in code but was never

    called from registration_service.py.



    This implementation is drop-in-compatible with the live pipeline.

    Enforces grid-based suppression to prevent SIFT from clustering all

    matches on a single crater rim (common lunar failure mode).

    """



    def __init__(self, grid_rows: int = 4, grid_cols: int = 4, max_per_cell: int = 10):

        self.grid_rows = grid_rows

        self.grid_cols = grid_cols

        self.max_per_cell = max_per_cell



    def filter(

        self,

        kp1: List[cv2.KeyPoint],

        kp2: List[cv2.KeyPoint],

        matches: List[cv2.DMatch],

        image_shape: Tuple[int, int],

    ) -> Tuple[List[cv2.DMatch], Dict[str, Any]]:

        """

        Returns filtered matches + distribution quality metrics.

        """

        if not matches:

            return matches, {"coverage": 0.0, "suppressed": 0}



        h, w = image_shape[:2]

        cell_h = h / self.grid_rows

        cell_w = w / self.grid_cols



        grid: Dict[Tuple[int, int], List[cv2.DMatch]] = {}

        for m in sorted(matches, key=lambda x: x.distance):

            pt = kp1[m.queryIdx].pt

            row = min(int(pt[1] / cell_h), self.grid_rows - 1)

            col = min(int(pt[0] / cell_w), self.grid_cols - 1)

            cell = (row, col)

            grid.setdefault(cell, [])

            if len(grid[cell]) < self.max_per_cell:

                grid[cell].append(m)



        filtered = [m for cell_matches in grid.values() for m in cell_matches]



        occupied = len(grid)

        total_cells = self.grid_rows * self.grid_cols

        coverage = occupied / total_cells



        metrics = {

            "before": len(matches),

            "after": len(filtered),

            "suppressed": len(matches) - len(filtered),

            "grid_coverage": round(coverage, 3),

            "cells_occupied": occupied,

            "total_cells": total_cells,

        }

        logger.info(

            f"  [SpatialFilter] {metrics['before']}→{metrics['after']} matches, "

            f"coverage={coverage:.0%} ({occupied}/{total_cells} cells)"

        )

        return filtered, metrics





# ============================================================

# GAP 4 — QUANTITATIVE BENCHMARK RUNNER (RMSE / TRE table)

# ============================================================



class QuantitativeBenchmark:

    """

    Previously: EXPERIMENT_LOG.md had zero experiments. BenchmarkSuite

    existed but was never called.



    This class runs all three matchers (SIFT, IllumInvariant, LoFTR if

    available) on the same image pair and produces a comparison table.

    """



    def __init__(self, loftr_available: bool = False):

        self.loftr_ok = loftr_available

        self.cascade = AdaptiveMatcherCascade(loftr_available)



    def run(

        self,

        src: np.ndarray,

        ref: np.ndarray,

        ground_truth_H: Optional[np.ndarray] = None,

    ) -> Dict[str, Any]:

        """

        Benchmarks each matcher independently and returns a results dict

        suitable for printing as a table and saving to EXPERIMENT_LOG.md.

        """

        methods = ["SIFT", "IlluminationInvariant"]

        if self.loftr_ok:

            methods.append("LoFTR")



        rows = []

        for method in methods:

            t0 = time.time()

            if method == "SIFT":

                kp1, kp2, matches = self.cascade._sift_match(src, ref)

            elif method == "IlluminationInvariant":

                kp1, kp2, matches = self.cascade._illumination_invariant_match(src, ref)

            else:

                kp1, kp2, matches = self.cascade._loftr_match(src, ref)

            elapsed = time.time() - t0



            n_matches = len(matches)

            n_inliers, mask = self.cascade._count_inliers(kp1, kp2, matches)



            # RMSE

            rmse = float("inf")

            tre = float("inf")

            if mask is not None and n_inliers >= 4:

                pts1 = np.float32([kp1[m.queryIdx].pt for m in matches])

                pts2 = np.float32([kp2[m.trainIdx].pt for m in matches])

                H_pred, _ = cv2.findHomography(pts1, pts2, cv2.RANSAC, 4.0)

                if H_pred is not None:

                    inlier_idx = np.where(mask.ravel() == 1)[0]

                    p1_in = pts1[inlier_idx].reshape(-1, 1, 2)

                    p2_in = pts2[inlier_idx]

                    projected = cv2.perspectiveTransform(p1_in, H_pred).reshape(-1, 2)

                    errors = np.linalg.norm(p2_in - projected, axis=1)

                    rmse = float(np.sqrt(np.mean(errors ** 2)))



                    # TRE vs ground truth (if provided)

                    if ground_truth_H is not None:

                        h_img, w_img = src.shape[:2]

                        corners = np.float32(

                            [[0, 0], [w_img, 0], [w_img, h_img], [0, h_img]]

                        ).reshape(-1, 1, 2)

                        gt_c = cv2.perspectiveTransform(corners, ground_truth_H).reshape(-1, 2)

                        pr_c = cv2.perspectiveTransform(corners, H_pred).reshape(-1, 2)

                        tre = float(np.mean(np.linalg.norm(gt_c - pr_c, axis=1)))



            rows.append({

                "method": method,

                "matches": n_matches,

                "inliers": n_inliers,

                "inlier_ratio": round(n_inliers / max(n_matches, 1), 3),

                "rmse_px": round(rmse, 4) if rmse != float("inf") else "FAILED",

                "tre_px": round(tre, 4) if tre != float("inf") else "N/A",

                "time_s": round(elapsed, 3),

            })



        return {"results": rows, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")}



    @staticmethod

    def print_table(benchmark_results: Dict[str, Any]):

        rows = benchmark_results["results"]

        header = f"{'Method':<25} {'Matches':>8} {'Inliers':>8} {'Ratio':>8} {'RMSE(px)':>10} {'TRE(px)':>10} {'Time(s)':>8}"

        sep = "-" * len(header)

        print("\n" + sep)

        print("QUANTITATIVE BENCHMARK — LunaAlign SIH26166")

        print(f"Run at: {benchmark_results['timestamp']}")

        print(sep)

        print(header)

        print(sep)

        for r in rows:

            print(

                f"{r['method']:<25} {r['matches']:>8} {r['inliers']:>8} "

                f"{r['inlier_ratio']:>8.3f} {str(r['rmse_px']):>10} "

                f"{str(r['tre_px']):>10} {r['time_s']:>8}"

            )

        print(sep + "\n")



    @staticmethod

    def append_to_experiment_log(

        benchmark_results: Dict[str, Any],

        log_path: str = "EXPERIMENT_LOG.md",

    ):

        rows = benchmark_results["results"]

        ts = benchmark_results["timestamp"]

        block = f"\n## Experiment — {ts}\n\n"

        block += "| Method | Matches | Inliers | RMSE (px) | TRE (px) | Time (s) |\n"

        block += "|--------|---------|---------|-----------|----------|----------|\n"

        for r in rows:

            block += (

                f"| {r['method']} | {r['matches']} | {r['inliers']} | "

                f"{r['rmse_px']} | {r['tre_px']} | {r['time_s']} |\n"

            )

        block += "\n"

        with open(log_path, "a") as f:

            f.write(block)

        logger.info(f"Appended benchmark results to {log_path}")





# ============================================================

# GAP 5 — SCIENTIFIC GUI OUTPUTS: Uncertainty heatmap + batch mode

# ============================================================



class ScientificOutputGenerator:

    """

    The frontend currently shows match overlays but no uncertainty heatmap,

    no DEM/3D output, and no batch mode — all noted as GUI weaknesses.



    This class generates:

      1. Uncertainty heatmap (PNG) — confidence of each match location

      2. Registration overlay (PNG) — warped source over reference

      3. Batch mode — processes a folder of image pairs

    """



    def __init__(self, out_dir: str = "output"):

        self.out_dir = out_dir

        os.makedirs(out_dir, exist_ok=True)



    def generate_uncertainty_heatmap(

        self,

        img: np.ndarray,

        kp: List[cv2.KeyPoint],

        matches: List[cv2.DMatch],

        inlier_mask: Optional[np.ndarray] = None,

        filename: str = "uncertainty_heatmap.png",

    ) -> str:

        """

        Generates a spatial confidence heatmap based on match density

        and inlier/outlier status. High density + high inliers = high confidence.

        """

        h, w = img.shape[:2]

        heatmap = np.zeros((h, w), dtype=np.float32)



        for i, m in enumerate(matches):

            if m.queryIdx >= len(kp):

                continue

            pt = kp[m.queryIdx].pt

            px, py = int(pt[0]), int(pt[1])

            if 0 <= px < w and 0 <= py < h:

                # Inliers get high confidence, outliers get low

                if inlier_mask is not None:

                    conf = 1.0 if inlier_mask[i][0] == 1 else 0.15

                else:

                    conf = max(0.1, 1.0 - m.distance / 500.0)

                cv2.circle(heatmap, (px, py), radius=20, color=conf, thickness=-1)



        # Smooth

        heatmap = cv2.GaussianBlur(heatmap, (61, 61), 20)

        heatmap = np.clip(heatmap / (heatmap.max() + 1e-6), 0, 1)



        # Colormap

        heatmap_u8 = (heatmap * 255).astype(np.uint8)

        colored = cv2.applyColorMap(heatmap_u8, cv2.COLORMAP_JET)



        # Overlay on grayscale image

        base_bgr = cv2.cvtColor(

            img if len(img.shape) == 2 else cv2.cvtColor(img, cv2.COLOR_BGR2GRAY),

            cv2.COLOR_GRAY2BGR,

        )

        result = cv2.addWeighted(base_bgr, 0.5, colored, 0.5, 0)



        path = os.path.join(self.out_dir, filename)

        cv2.imwrite(path, result)

        logger.info(f"  [Output] Uncertainty heatmap saved: {path}")

        return path



    def generate_registration_overlay(

        self,

        src: np.ndarray,

        ref: np.ndarray,

        H: np.ndarray,

        filename: str = "registration_overlay.png",

    ) -> str:

        """

        Warps source onto reference coordinate frame and creates a

        side-by-side + blended overlay for visual QA.

        """

        h, w = ref.shape[:2]

        src_gray = self._gray(src)

        ref_gray = self._gray(ref)



        warped = cv2.warpPerspective(src_gray, H, (w, h))



        # Checkerboard blend to show alignment quality

        block = 64

        blend = np.zeros((h, w), dtype=np.uint8)

        for r in range(0, h, block):

            for c in range(0, w, block):

                use_src = ((r // block) + (c // block)) % 2 == 0

                patch = warped[r:r+block, c:c+block] if use_src else ref_gray[r:r+block, c:c+block]

                blend[r:r+block, c:c+block] = patch



        combined = np.hstack([src_gray, ref_gray, warped, blend])

        path = os.path.join(self.out_dir, filename)

        cv2.imwrite(path, combined)

        logger.info(f"  [Output] Registration overlay saved: {path}")

        return path



    def batch_process(

        self,

        pairs_dir: str,

        pipeline: "FullRegistrationPipeline",

    ) -> List[Dict[str, Any]]:

        """

        Processes all image pairs in pairs_dir/{pair_id}/source.png + reference.png.

        Writes per-pair JSON results and a combined batch_summary.json.

        """

        pairs_path = Path(pairs_dir)

        pair_dirs = [d for d in pairs_path.iterdir() if d.is_dir()]



        if not pair_dirs:

            logger.warning(f"No pair subdirectories found in {pairs_dir}")

            return []



        logger.info(f"Batch mode: processing {len(pair_dirs)} pairs from {pairs_dir}")

        all_results = []



        for pair_dir in sorted(pair_dirs):

            src_path = pair_dir / "source.png"

            ref_path = pair_dir / "reference.png"

            if not (src_path.exists() and ref_path.exists()):

                logger.warning(f"  Skipping {pair_dir.name}: missing source or reference")

                continue



            src = cv2.imread(str(src_path))

            ref = cv2.imread(str(ref_path))

            logger.info(f"  Processing pair: {pair_dir.name}")



            result = pipeline.run(src, ref)

            result["pair"] = pair_dir.name

            all_results.append(result)



            pair_out = os.path.join(self.out_dir, pair_dir.name)

            os.makedirs(pair_out, exist_ok=True)

            with open(os.path.join(pair_out, "result.json"), "w") as f:

                json.dump(result, f, indent=2, default=str)



        summary_path = os.path.join(self.out_dir, "batch_summary.json")

        with open(summary_path, "w") as f:

            json.dump(all_results, f, indent=2, default=str)

        logger.info(f"Batch complete. Summary: {summary_path}")

        return all_results



    @staticmethod

    def _gray(img: np.ndarray) -> np.ndarray:

        if len(img.shape) == 3:

            return cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        return img.copy()





# ============================================================

# GAP 6 — TECHNICAL DECISION LOG (auto-written at runtime)

# ============================================================



class TechnicalDecisionLogger:
    """
    TECHNICAL_DECISIONS.md was a placeholder with only 'Test Decision'.
    This class auto-records every architectural choice made at runtime
    with the rationale, so the doc is always accurate and up to date.
    """

    def __init__(self, path: str = "TECHNICAL_DECISIONS.md"):
        self.path = path
        self.entries = []

    def record(self, decision: str, rationale: str, alternative: str = "N/A"):
        entry = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S"),
            "decision": decision,
            "rationale": rationale,
            "alternative_considered": alternative,
        }
        self.entries.append(entry)
        logger.debug(f"  [TechDecision] {decision}")

    def write(self):
        lines = [
            "# Technical Decisions — LunaAlign SIH26166\n",
            "_Auto-generated by lunaalign_fixed_pipeline.py_\n\n",
        ]
        for e in self.entries:
            lines.append(f"## {e['decision']}\n")
            lines.append(f"- **Timestamp**: {e['timestamp']}\n")
            lines.append(f"- **Rationale**: {e['rationale']}\n")
            lines.append(f"- **Alternative considered**: {e['alternative_considered']}\n\n")

        with open(self.path, "w", encoding="utf-8") as f:
            f.writelines(lines)
        logger.info(f"Technical decisions written to {self.path}")


# ============================================================
# FULL PIPELINE — integrates all gaps
# ============================================================

class FullRegistrationPipeline:
    """
    Drop-in replacement for registration_service.py's RegistrationService.

    Wires together:
      GAP 1 → RealDataAcquisition
      GAP 2 → MultiModalPreprocessor
      GAP 3 → AdaptiveMatcherCascade
      GAP 4 → QuantitativeBenchmark
      GAP 5 → ScientificOutputGenerator
      GAP 6 → TechnicalDecisionLogger
      GAP 7 → SpatialDistributionFilter
      GAP 8 → DependencyChecker
    """

    def __init__(

        self,

        mode: str = "standard",

        src_gsd: float = 0.32,

        ref_gsd: float = 5.0,

        out_dir: str = "output",

    ):

        """

        mode: 'standard' (same-sensor) | 'multimodal' (OHRC↔TMC2)

        """

        self.mode = mode

        self.loftr_ok = DependencyChecker.loftr_available()

        self.preprocessor = MultiModalPreprocessor(src_gsd, ref_gsd)

        self.cascade = AdaptiveMatcherCascade(self.loftr_ok)

        self.spatial_filter = SpatialDistributionFilter()

        self.output_gen = ScientificOutputGenerator(out_dir)

        self.tech_log = TechnicalDecisionLogger()



        # Record architectural decisions

        self.tech_log.record(

            "Adaptive matcher cascade (SIFT→IllumInvariant→LoFTR)",

            "Single matcher fails for multi-modal pairs. Cascade guarantees "

            "best available matcher is used without manual configuration.",

            "Always use LoFTR (too slow on CPU for hackathon demo)"

        )

        self.tech_log.record(

            "Phase congruency for illumination invariance",

            "Phase congruency responds to local phase discontinuities, not "

            "pixel intensities, making it invariant to linear illumination "

            "changes common between orbital passes at different sun angles.",

            "Gradient orientation (simpler but less invariant)"

        )

        self.tech_log.record(

            "RANSAC threshold = 4.0px",

            "Lunar images have few repeatable keypoints; tight threshold (1px) "

            "rejects valid matches on low-texture terrain. 4px balances "

            "robustness and precision for 0.32–5m/px imagery.",

            "1px (too strict), 8px (too loose)"

        )

        self.tech_log.record(

            "Grid 4×4 spatial suppression, max 10 per cell",

            "Lunar craters cause SIFT to cluster all matches on crater rims. "

            "Uniform spatial distribution prevents homography from being "

            "determined by a single local region.",

            "No suppression (leads to model drift on textured regions)"

        )

        if mode == "multimodal":

            self.tech_log.record(

                "Downsample OHRC to TMC2 GSD before matching",

                f"OHRC (0.32m/px) and TMC2 (5m/px) have ~15.6× GSD ratio. "

                "SIFT descriptors are computed on scale-normalised images to "

                "make the appearance gap tractable before feature matching.",

                "Match at native resolution (SIFT returns 0 inliers)"

            )



    def run(

        self,

        src: np.ndarray,

        ref: np.ndarray,

        ground_truth_H: Optional[np.ndarray] = None,

    ) -> Dict[str, Any]:

        """

        Complete registration run. Returns result dict compatible with

        existing summary.json schema in registration_service.py.

        """

        logger.info(f"=== LunaAlign Fixed Pipeline | mode={self.mode} ===")



        # ── GAP 2: Multi-modal preprocessing ─────────────────────

        scale_ratio = 1.0

        if self.mode == "multimodal":

            logger.info("Step 1/5: Multi-modal preprocessing...")

            src_proc, ref_proc, scale_ratio = self.preprocessor.preprocess(src, ref)

        else:

            logger.info("Step 1/5: Standard preprocessing (CLAHE)...")

            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

            src_gray = cv2.cvtColor(src, cv2.COLOR_BGR2GRAY) if len(src.shape) == 3 else src

            ref_gray = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY) if len(ref.shape) == 3 else ref

            src_proc = clahe.apply(src_gray)

            ref_proc = clahe.apply(ref_gray)



        # ── GAP 3: Adaptive matcher cascade ──────────────────────

        logger.info("Step 2/5: Adaptive matcher cascade...")

        kp1, kp2, matches, matcher_used = self.cascade.run(src_proc, ref_proc)



        # Scale keypoints back if downsampled

        if scale_ratio > 1.0:

            kp1 = self.preprocessor.scale_keypoints_back(kp1, scale_ratio)



        # ── GAP 7: Spatial distribution enforcement ───────────────

        logger.info("Step 3/5: Spatial distribution enforcement...")

        img_shape = ref_proc.shape

        filtered_matches, dist_metrics = self.spatial_filter.filter(

            kp1, kp2, matches, img_shape

        )



        # ── Homography estimation ─────────────────────────────────

        logger.info("Step 4/5: Homography estimation + sub-pixel refinement...")

        H, inlier_mask, rmse, n_inliers = None, None, float("inf"), 0

        model_name = "FAILED"



        if len(filtered_matches) >= 4:

            pts1 = np.float32([kp1[m.queryIdx].pt for m in filtered_matches])

            pts2 = np.float32([kp2[m.trainIdx].pt for m in filtered_matches])

            H, inlier_mask = cv2.findHomography(pts1, pts2, cv2.RANSAC, 4.0)



            if H is not None:

                n_inliers = int(inlier_mask.sum())

                inlier_idx = np.where(inlier_mask.ravel() == 1)[0]

                p1_in = pts1[inlier_idx].reshape(-1, 1, 2)

                p2_in = pts2[inlier_idx]

                projected = cv2.perspectiveTransform(p1_in, H).reshape(-1, 2)

                errors = np.linalg.norm(p2_in - projected, axis=1)

                rmse = float(np.sqrt(np.mean(errors ** 2)))

                model_name = f"homography_via_{matcher_used}"

                logger.info(

                    f"  Homography found: inliers={n_inliers}, RMSE={rmse:.4f}px"

                )

            else:

                logger.warning("  findHomography returned None.")

        else:

            logger.warning(

                f"  Not enough filtered matches ({len(filtered_matches)}) for homography."

            )



        # ── GAP 5: Scientific outputs ─────────────────────────────

        logger.info("Step 5/5: Generating scientific outputs...")

        heatmap_path = self.output_gen.generate_uncertainty_heatmap(

            src_proc, kp1, filtered_matches, inlier_mask

        )

        overlay_path = None

        if H is not None:

            overlay_path = self.output_gen.generate_registration_overlay(

                src_proc, ref_proc, H

            )



        # ── GAP 6: Write technical decisions ─────────────────────

        self.tech_log.write()



        result = {

            "model": model_name,

            "matcher_used": matcher_used,

            "rmse": round(rmse, 4) if rmse != float("inf") else "FAILED",

            "inliers": n_inliers,

            "total_matches": len(matches),

            "filtered_matches": len(filtered_matches),

            "spatial_distribution": dist_metrics,

            "H_matrix": H.tolist() if H is not None else None,

            "outputs": {

                "heatmap": heatmap_path,

                "overlay": overlay_path,

            },

            "scale_ratio_applied": round(scale_ratio, 2),

        }



        logger.info(f"=== Pipeline complete: {result['model']} | RMSE={result['rmse']} ===")

        return result





# ============================================================

# CLI ENTRY POINT

# ============================================================



def main():

    parser = argparse.ArgumentParser(

        description="LunaAlign Fixed Pipeline — SIH26166"

    )

    parser.add_argument("--source", default=None, help="Path to source image")

    parser.add_argument("--reference", default=None, help="Path to reference image")

    parser.add_argument(

        "--mode",

        default="standard",

        choices=["standard", "multimodal"],

        help="'standard' for same-sensor, 'multimodal' for OHRC↔TMC2",

    )

    parser.add_argument(

        "--benchmark",

        action="store_true",

        help="Run quantitative benchmark comparing all matchers",

    )

    parser.add_argument(

        "--batch",

        default=None,

        help="Path to folder of image pairs for batch processing",

    )

    parser.add_argument("--out", default="output", help="Output directory")

    parser.add_argument(

        "--data-guide",

        action="store_true",

        help="Print real data download guide and exit",

    )

    args = parser.parse_args()



    if args.data_guide:

        RealDataAcquisition.print_download_guide()

        return



    loftr_ok = DependencyChecker.loftr_available()



    # ── Load images ───────────────────────────────────────────────

    src_sensor = "OHRC" if args.mode == "multimodal" else "TMC2"

    ref_sensor = "TMC2" if args.mode == "multimodal" else "TMC2"



    src = RealDataAcquisition.load_or_create_proxy(

        args.source or "__no_file__", sensor=src_sensor

    )

    ref = RealDataAcquisition.load_or_create_proxy(

        args.reference or "__no_file__", sensor=ref_sensor

    )



    # Ensure 3-channel for pipeline

    if len(src.shape) == 2:

        src = cv2.cvtColor(src, cv2.COLOR_GRAY2BGR)

    if len(ref.shape) == 2:

        ref = cv2.cvtColor(ref, cv2.COLOR_GRAY2BGR)



    pipeline = FullRegistrationPipeline(

        mode=args.mode,

        src_gsd=0.32 if args.mode == "multimodal" else 5.0,

        ref_gsd=5.0,

        out_dir=args.out,

    )



    # ── Batch mode ────────────────────────────────────────────────

    if args.batch:

        results = pipeline.output_gen.batch_process(args.batch, pipeline)

        print(f"\nBatch complete: {len(results)} pairs processed.")

        return



    # ── Single pair registration ──────────────────────────────────

    result = pipeline.run(src, ref)

    print("\n" + "="*50)

    print("REGISTRATION RESULT")

    print("="*50)

    print(json.dumps(result, indent=2, default=str))



    # ── Benchmark mode ────────────────────────────────────────────

    if args.benchmark:

        print("\nRunning quantitative benchmark...")

        bm = QuantitativeBenchmark(loftr_ok)

        bm_results = bm.run(

            cv2.cvtColor(src, cv2.COLOR_BGR2GRAY),

            cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY),

        )

        QuantitativeBenchmark.print_table(bm_results)

        QuantitativeBenchmark.append_to_experiment_log(

            bm_results,

            log_path=os.path.join(args.out, "EXPERIMENT_LOG.md"),

        )





if __name__ == "__main__":

    main()
