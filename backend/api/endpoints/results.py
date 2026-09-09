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


# NEW ENDPOINT: Serve raw source and reference images
@router.get("/{session_id}/image/{img_type}")
async def get_raw_image(session_id: str, img_type: str):
    """
    Returns the raw source or reference image for a session.
    img_type can be: 'source' or 'reference'
    """
    logger.info(f"Request for raw image: session={session_id}, type={img_type}")
    mapping = {
        'source': "source.png",
        'reference': "reference.png"
    }

    if img_type not in mapping:
        logger.warning(f"Invalid image type requested: {img_type}")
        raise HTTPException(status_code=400, detail="Invalid image type request")

    path = f"backend/cache/images/{session_id}/{mapping[img_type]}"
    if not os.path.exists(path):
        logger.warning(f"Image not found: {path}")
        raise HTTPException(status_code=404, detail="Image not found")

    logger.info(f"Serving raw image: {path}")
    return FileResponse(path)


# ============================================================
# GAP 4 — BENCHMARK ENDPOINT
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
# GAP 5 — SCIENTIFIC OUTPUT ENDPOINTS
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



# ============================================================
# GAP 4 — BENCHMARK ENDPOINT
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
# GAP 5 — SCIENTIFIC OUTPUT ENDPOINTS
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