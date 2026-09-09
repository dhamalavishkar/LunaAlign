from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import uuid
import os
import shutil
import json
import cv2
import logging

from src.data.io.format_handlers.img_reader import extract_img_preview, read_img
from src.data.io.format_detection import detect_format

router = APIRouter()
logger = logging.getLogger(__name__)

DOWNLOADS_DIR = os.path.expanduser(r"~\Downloads")

@router.post("/")
async def upload_image_pair(source: UploadFile = File(...), reference: UploadFile = File(...)):
    """
    Ingests binary image payloads (PNG, JPEG, TIFF, or PDS3 / raw .IMG planetary files),
    allocates a unique session ID, and autonomously generates web-renderable previews.
    """
    if not source.filename or not reference.filename:
        raise HTTPException(status_code=400, detail="Both source and reference files are required")
        
    session_id = str(uuid.uuid4())
    session_dir = f"backend/cache/images/{session_id}"
    os.makedirs(session_dir, exist_ok=True)
    
    src_ext = os.path.splitext(source.filename)[1].lower() or ".png"
    ref_ext = os.path.splitext(reference.filename)[1].lower() or ".png"
    
    src_path = os.path.join(session_dir, f"source{src_ext}")
    ref_path = os.path.join(session_dir, f"reference{ref_ext}")
    
    try:
        with open(src_path, "wb") as f_src:
            shutil.copyfileobj(source.file, f_src)
            
        with open(ref_path, "wb") as f_ref:
            shutil.copyfileobj(reference.file, f_ref)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to cache files: {str(e)}")
    finally:
        source.file.close()
        reference.file.close()

    # Generate web-renderable previews for both files
    src_preview_path = os.path.join(session_dir, "source_preview.png")
    ref_preview_path = os.path.join(session_dir, "reference_preview.png")
    
    src_meta = {}
    ref_meta = {}

    try:
        if src_ext in [".img", ".bin", ".dat", ".raw", ".lbl"]:
            extract_img_preview(src_path, src_preview_path, max_dim=1024)
            _, src_meta = read_img(src_path, max_dim=1024)
        else:
            img = cv2.imread(src_path)
            if img is not None:
                cv2.imwrite(src_preview_path, img)
            else:
                extract_img_preview(src_path, src_preview_path, max_dim=1024)
    except Exception as e:
        logger.warning(f"Failed to generate source preview: {e}")

    try:
        if ref_ext in [".img", ".bin", ".dat", ".raw", ".lbl"]:
            extract_img_preview(ref_path, ref_preview_path, max_dim=1024)
            _, ref_meta = read_img(ref_path, max_dim=1024)
        else:
            img = cv2.imread(ref_path)
            if img is not None:
                cv2.imwrite(ref_preview_path, img)
            else:
                extract_img_preview(ref_path, ref_preview_path, max_dim=1024)
    except Exception as e:
        logger.warning(f"Failed to generate reference preview: {e}")

    # Ensure source.png and reference.png exist for downstream web components & DEM service
    src_png_path = os.path.join(session_dir, "source.png")
    ref_png_path = os.path.join(session_dir, "reference.png")
    try:
        if not os.path.exists(src_png_path) and os.path.exists(src_preview_path):
            shutil.copyfile(src_preview_path, src_png_path)
        if not os.path.exists(ref_png_path) and os.path.exists(ref_preview_path):
            shutil.copyfile(ref_preview_path, ref_png_path)
    except Exception as e:
        logger.warning(f"Failed to copy preview to standard PNG: {e}")

    manifest = {
        "session_id": session_id,
        "source_filename": source.filename,
        "source_path": src_path,
        "source_ext": src_ext,
        "source_metadata": src_meta,
        "reference_filename": reference.filename,
        "reference_path": ref_path,
        "reference_ext": ref_ext,
        "reference_metadata": ref_meta
    }

    with open(os.path.join(session_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return {
        "session_id": session_id,
        "message": "Images successfully cached and ready for registration.",
        "source_preview": f"/api/v1/upload/preview/{session_id}/source",
        "reference_preview": f"/api/v1/upload/preview/{session_id}/reference",
        "source_metadata": src_meta,
        "reference_metadata": ref_meta
    }


@router.get("/preview/{session_id}/{image_type}")
def get_image_preview(session_id: str, image_type: str):
    """
    Returns the visual preview thumbnail for a loaded image (source or reference).
    """
    preview_file = f"backend/cache/images/{session_id}/{image_type}_preview.png"
    if os.path.exists(preview_file):
        return FileResponse(preview_file, media_type="image/png")
        
    # Fallback to standard png if preview wasn't explicitly generated
    fallback = f"backend/cache/images/{session_id}/{image_type}.png"
    if os.path.exists(fallback):
        return FileResponse(fallback, media_type="image/png")
        
    raise HTTPException(status_code=404, detail="Preview not found")


@router.post("/load-local-real")
def load_local_real_images(pair_type: str = "cross_track_stereo"):
    """
    Directly allocates a session using the user's downloaded real LROC .IMG files
    (M104311715LE.IMG & M104311715RE.IMG or M104318871) without needing 500MB browser HTTP upload.
    """
    candidates = [
        os.path.join(DOWNLOADS_DIR, "M104311715LE.IMG"),
        os.path.join(DOWNLOADS_DIR, "M104311715RE.IMG"),
        os.path.join(DOWNLOADS_DIR, "M104318871LE.IMG"),
        os.path.join(DOWNLOADS_DIR, "M104318871RE.IMG"),
    ]

    # Also check demo or data folder
    src_img_path = candidates[0]
    ref_img_path = candidates[1] if pair_type == "cross_track_stereo" else candidates[2]

    if not os.path.exists(src_img_path) or not os.path.exists(ref_img_path):
        raise HTTPException(
            status_code=404, 
            detail=f"Real .IMG files not found in {DOWNLOADS_DIR}. Expected M104311715LE.IMG and RE/LE."
        )

    session_id = str(uuid.uuid4())
    session_dir = f"backend/cache/images/{session_id}"
    os.makedirs(session_dir, exist_ok=True)

    dest_src = os.path.join(session_dir, "source.img")
    dest_ref = os.path.join(session_dir, "reference.img")

    # Fast copy or symlink
    shutil.copyfile(src_img_path, dest_src)
    shutil.copyfile(ref_img_path, dest_ref)

    # Generate previews
    src_preview_path = os.path.join(session_dir, "source_preview.png")
    ref_preview_path = os.path.join(session_dir, "reference_preview.png")
    
    extract_img_preview(dest_src, src_preview_path, max_dim=1024)
    extract_img_preview(dest_ref, ref_preview_path, max_dim=1024)
    
    _, src_meta = read_img(dest_src, max_dim=1024)
    _, ref_meta = read_img(dest_ref, max_dim=1024)

    manifest = {
        "session_id": session_id,
        "source_filename": os.path.basename(src_img_path),
        "source_path": dest_src,
        "source_ext": ".img",
        "source_metadata": src_meta,
        "reference_filename": os.path.basename(ref_img_path),
        "reference_path": dest_ref,
        "reference_ext": ".img",
        "reference_metadata": ref_meta
    }

    with open(os.path.join(session_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return {
        "session_id": session_id,
        "message": "Real LROC NAC .IMG files loaded successfully.",
        "source_filename": os.path.basename(src_img_path),
        "reference_filename": os.path.basename(ref_img_path),
        "source_preview": f"/api/v1/upload/preview/{session_id}/source",
        "reference_preview": f"/api/v1/upload/preview/{session_id}/reference",
        "source_metadata": src_meta,
        "reference_metadata": ref_meta
    }
