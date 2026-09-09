from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
import os
import json

router = APIRouter()

@router.get("/{session_id}/summary")
async def get_summary(session_id: str):
    """
    Returns the JSON payload containing RMSE, Inliers, and Transformation matrices.
    """
    path = f"backend/cache/results/{session_id}/summary.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Results not found or still processing")

    with open(path, "r") as f:
        return json.load(f)

@router.get("/{session_id}/dossier/{idx}")
async def get_dossier(session_id: str, idx: int):
    """
    Returns the explainability dossier for a specific match index.
    """
    path = f"backend/cache/results/{session_id}/dossier_{idx}.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Dossier not found")

    with open(path, "r") as f:
        return json.load(f)

import logging
logger = logging.getLogger(__name__)

@router.get("/{session_id}/dossier/{idx}/image/{img_type}")
async def get_dossier_image(session_id: str, idx: int, img_type: str):
    """
    Returns the binary visual files for the frontend dashboard.
    img_type can be: 'patch', 'src_uncertainty', 'ref_uncertainty'
    """
    logger.info(f"Request for dossier image: session={session_id}, idx={idx}, type={img_type}")
    mapping = {
        'patch': f"match_patch_{idx}.png",
        'src_uncertainty': f"uncertainty_kp_{idx}_src.png",
        "ref_uncertainty": f"uncertainty_kp_{idx}_ref.png"
    }

    if img_type not in mapping:
        logger.warning(f"Invalid image type requested: {img_type}")
        raise HTTPException(status_code=400, detail="Invalid image type request")

    path = f"backend/cache/results/{session_id}/{mapping[img_type]}"
    if not os.path.exists(path):
        logger.warning(f"Image not found: {path}")
        raise HTTPException(status_code=404, detail="Image not found")

    logger.info(f"Serving image: {path}")
    return FileResponse(path)


# Serve raw source, reference, and registered warped images
@router.get("/{session_id}/image/{img_type}")
async def get_raw_image(session_id: str, img_type: str):
    """
    Returns the web-renderable source, reference, or warped reference image for a session.
    img_type can be: 'source', 'reference', or 'warped'
    """
    logger.info(f"Request for image: session={session_id}, type={img_type}")
    
    if img_type == 'warped':
        # Check pre-computed warped reference or registration overlay
        warped_path = f"backend/cache/results/{session_id}/warped_reference.png"
        if os.path.exists(warped_path):
            return FileResponse(warped_path, media_type="image/png")
            
        overlay_path = f"backend/cache/results/{session_id}/registration_overlay.png"
        if os.path.exists(overlay_path):
            return FileResponse(overlay_path, media_type="image/png")

        # Attempt on-the-fly warping if summary.json has H_matrix
        summary_path = f"backend/cache/results/{session_id}/summary.json"
        if os.path.exists(summary_path):
            try:
                with open(summary_path, "r") as f:
                    summary = json.load(f)
                H = summary.get("H_matrix")
                if H is not None:
                    import cv2
                    import numpy as np
                    H_mat = np.array(H, dtype=np.float32)
                    if np.linalg.matrix_rank(H_mat) == 3:
                        H_inv = np.linalg.inv(H_mat)
                        # Find source and reference
                        session_img_dir = f"backend/cache/images/{session_id}"
                        ref_p = os.path.join(session_img_dir, "reference.png")
                        if not os.path.exists(ref_p):
                            ref_p = os.path.join(session_img_dir, "reference_preview.png")
                        src_p = os.path.join(session_img_dir, "source.png")
                        if not os.path.exists(src_p):
                            src_p = os.path.join(session_img_dir, "source_preview.png")

                        if os.path.exists(ref_p) and os.path.exists(src_p):
                            ref_img = cv2.imread(ref_p)
                            src_img = cv2.imread(src_p)
                            if ref_img is not None and src_img is not None:
                                warped = cv2.warpPerspective(ref_img, H_inv, (src_img.shape[1], src_img.shape[0]))
                                os.makedirs(f"backend/cache/results/{session_id}", exist_ok=True)
                                cv2.imwrite(warped_path, warped)
                                return FileResponse(warped_path, media_type="image/png")
            except Exception as e:
                logger.warning(f"On-the-fly warping failed for session {session_id}: {e}")

        # Fall back to reference image if warp unavailable
        img_type = 'reference'

    if img_type not in ['source', 'reference']:
        logger.warning(f"Invalid image type requested: {img_type}")
        raise HTTPException(status_code=400, detail="Invalid image type request. Use 'source', 'reference', or 'warped'.")

    session_img_dir = f"backend/cache/images/{session_id}"
    candidates = [
        f"{img_type}.png",
        f"{img_type}_preview.png",
        f"{img_type}.jpg",
        f"{img_type}.jpeg",
        f"{img_type}.tif",
        f"{img_type}.tiff",
    ]

    for c in candidates:
        p = os.path.join(session_img_dir, c)
        if os.path.exists(p):
            media_type = "image/png" if c.endswith(".png") else "image/jpeg"
            return FileResponse(p, media_type=media_type)

    # If only raw scientific files exist (e.g. source.img), generate a preview on the fly
    if os.path.exists(session_img_dir):
        raw_files = [f for f in os.listdir(session_img_dir) if f.startswith(img_type + ".")]
        if raw_files:
            raw_path = os.path.join(session_img_dir, raw_files[0])
            preview_path = os.path.join(session_img_dir, f"{img_type}.png")
            try:
                from src.data.io.format_handlers.img_reader import extract_img_preview
                extract_img_preview(raw_path, preview_path, max_dim=1024)
                if os.path.exists(preview_path):
                    return FileResponse(preview_path, media_type="image/png")
            except Exception as e:
                logger.warning(f"Failed on-the-fly preview generation for {raw_path}: {e}")

    logger.warning(f"Image not found in session {session_id} for type {img_type}")
    raise HTTPException(status_code=404, detail="Image not found")



# ============================================================
# BENCHMARK ENDPOINT
# ============================================================

@router.get("/{session_id}/benchmark")
async def get_benchmark(session_id: str):
    """Returns the quantitative benchmark results (SIFT vs IllumInvariant vs LoFTR)."""
    path = f"backend/cache/results/{session_id}/benchmark.json"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Benchmark results not found. Run benchmark first.")
    with open(path, "r") as f:
        return json.load(f)


# ============================================================
# SCIENTIFIC OUTPUT ENDPOINTS
# ============================================================

@router.get("/{session_id}/heatmap")
async def get_uncertainty_heatmap(session_id: str):
    """Returns the uncertainty/confidence heatmap image."""
    path = f"backend/cache/results/{session_id}/uncertainty_heatmap.png"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Heatmap not found")
    return FileResponse(path, media_type="image/png")


@router.get("/{session_id}/overlay")
async def get_registration_overlay(session_id: str):
    """Returns the registration overlay (checkerboard blend) image."""
    path = f"backend/cache/results/{session_id}/registration_overlay.png"
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Overlay not found")
    return FileResponse(path, media_type="image/png")