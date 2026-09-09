import os
import re
import cv2
import numpy as np
from typing import Tuple, Dict, Any, Optional

def parse_pds3_header(file_path: str) -> Dict[str, Any]:
    """
    Parses attached or detached PDS3 header keywords.
    Returns a dictionary of key-value pairs and image object attributes.
    """
    header_dict: Dict[str, Any] = {}
    
    # Check if there is a detached .LBL or .lbl file
    base, _ = os.path.splitext(file_path)
    label_path = file_path
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File does not exist: {file_path}")
        
    for candidate in [base + ".LBL", base + ".lbl", base + ".xml"]:
        if os.path.exists(candidate):
            label_path = candidate
            break

    # Read up to first 64KB for attached label, or full file for detached .LBL
    try:
        with open(label_path, "rb") as f:
            raw_bytes = f.read(131072)
    except Exception as e:
        raise ValueError(f"Could not open label/file {label_path}: {e}")

    # Decode header
    header_text = raw_bytes.decode("latin1", errors="replace")
    
    # Locate END keyword (end of PDS3 header)
    end_match = re.search(r"\bEND\b", header_text)
    if end_match:
        header_text = header_text[:end_match.start() + 4]

    # Parse PDS key = value pairs
    in_image_object = False
    image_attrs: Dict[str, Any] = {}
    
    for line in header_text.splitlines():
        line = line.strip()
        if not line or line.startswith("/*"):
            continue
            
        if line.startswith("OBJECT") and "IMAGE" in line:
            in_image_object = True
            continue
        elif line.startswith("END_OBJECT") and "IMAGE" in line:
            in_image_object = False
            continue
            
        if "=" in line:
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            # Remove inline comments
            if "/*" in v:
                v = v[:v.index("/*")].strip()
            # Remove units like <degC> or <nm>
            v_clean = re.sub(r"<.*?>", "", v).strip()
            
            # Type cast numbers where possible
            if v_clean.isdigit():
                val: Any = int(v_clean)
            else:
                try:
                    val = float(v_clean)
                except ValueError:
                    val = v_clean
                    
            if in_image_object:
                image_attrs[k] = val
            else:
                header_dict[k] = val

    header_dict["IMAGE_OBJECT"] = image_attrs
    return header_dict


def read_pds3_img(
    file_path: str,
    max_dim: Optional[int] = None,
    normalize_contrast: bool = True
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Reads a PDS3 attached/detached IMG file using memory mapping.
    Handles large lunar orbiter imagery (e.g., LROC NAC, Chandrayaan TMC/OHRC).
    """
    header = parse_pds3_header(file_path)
    img_obj = header.get("IMAGE_OBJECT", {})
    
    # Determine dimensions
    lines = img_obj.get("LINES") or header.get("LINES")
    samples = img_obj.get("LINE_SAMPLES") or header.get("LINE_SAMPLES")
    sample_bits = img_obj.get("SAMPLE_BITS") or header.get("SAMPLE_BITS", 8)
    sample_type = str(img_obj.get("SAMPLE_TYPE") or header.get("SAMPLE_TYPE", "LSB_INTEGER")).upper()
    record_bytes = header.get("RECORD_BYTES", 5064)
    label_records = header.get("LABEL_RECORDS", 1)
    image_ptr = header.get("^IMAGE", 2)
    
    # Calculate byte offset to raster data
    if isinstance(image_ptr, int):
        # Record pointer: (record_number - 1) * RECORD_BYTES
        byte_offset = (image_ptr - 1) * record_bytes
    elif isinstance(image_ptr, str) and image_ptr.isdigit():
        byte_offset = (int(image_ptr) - 1) * record_bytes
    else:
        # Fallback to label_records * record_bytes
        byte_offset = label_records * record_bytes

    if not lines or not samples:
        # Fallback: calculate from file size
        file_size = os.path.getsize(file_path)
        data_size = file_size - byte_offset
        bytes_per_sample = max(1, sample_bits // 8)
        total_pixels = data_size // bytes_per_sample
        # If record_bytes matches sample count (common in PDS fixed length)
        if record_bytes > 0 and (data_size % record_bytes == 0):
            samples = record_bytes // bytes_per_sample
            lines = total_pixels // samples
        else:
            dim = int(np.sqrt(total_pixels))
            lines, samples = dim, dim

    lines = int(lines)
    samples = int(samples)
    
    # Determine NumPy dtype
    is_msb = any(m in sample_type for m in ["MSB", "SUN", "MAC", "HIGH"])
    if sample_bits == 8:
        dtype = np.uint8
    elif sample_bits == 16:
        is_signed = "SIGNED" in sample_type and "UNSIGNED" not in sample_type
        if is_signed:
            dtype = np.dtype(">i2" if is_msb else "<i2")
        else:
            dtype = np.dtype(">u2" if is_msb else "<u2")
    elif sample_bits == 32:
        is_real = "REAL" in sample_type or "FLOAT" in sample_type
        if is_real:
            dtype = np.dtype(">f4" if is_msb else "<f4")
        else:
            dtype = np.dtype(">i4" if is_msb else "<i4")
    else:
        dtype = np.uint8

    # Memory map the raster to avoid huge RAM footprint
    try:
        mmap_arr = np.memmap(
            file_path,
            dtype=dtype,
            mode="r",
            offset=byte_offset,
            shape=(lines, samples)
        )
    except Exception as e:
        # If shape exceeds file size, clamp lines
        file_size = os.path.getsize(file_path)
        available_bytes = file_size - byte_offset
        itemsize = np.dtype(dtype).itemsize
        available_pixels = available_bytes // itemsize
        clamped_lines = available_pixels // samples
        if clamped_lines > 0:
            mmap_arr = np.memmap(
                file_path,
                dtype=dtype,
                mode="r",
                offset=byte_offset,
                shape=(clamped_lines, samples)
            )
            lines = clamped_lines
        else:
            raise ValueError(f"Failed to memory map PDS IMG {file_path}: {e}")

    # Downsample if image is huge and max_dim is specified
    scale_factor = 1.0
    if max_dim is not None and (lines > max_dim or samples > max_dim):
        step = int(np.ceil(max(lines, samples) / max_dim))
        raw_raster = np.array(mmap_arr[::step, ::step])
        scale_factor = 1.0 / step
    else:
        # If image is small enough or max_dim is None, copy or slice
        # For safety on large arrays, cap default in-memory copy at 4096 if max_dim was omitted
        if max_dim is None and max(lines, samples) > 4096:
            step = int(np.ceil(max(lines, samples) / 2048))
            raw_raster = np.array(mmap_arr[::step, ::step])
            scale_factor = 1.0 / step
        else:
            raw_raster = np.array(mmap_arr)

    # Scientific contrast stretching (1st to 99th percentile)
    if normalize_contrast:
        p1, p99 = np.percentile(raw_raster, (1, 99))
        if p99 > p1:
            clipped = np.clip(raw_raster, p1, p99)
            norm_img = ((clipped - p1) / (p99 - p1) * 255.0).astype(np.uint8)
        else:
            norm_img = cv2.normalize(raw_raster, None, 0, 255, cv2.NORM_MINMAX, dtype=cv2.CV_8U)
    else:
        norm_img = raw_raster

    metadata = {
        "format": "PDS3_IMG",
        "source_file": file_path,
        "original_dimensions": (lines, samples),
        "output_dimensions": norm_img.shape,
        "sample_bits": sample_bits,
        "sample_type": str(sample_type),
        "scale_applied": scale_factor,
        "product_id": header.get("PRODUCT_ID", "UNKNOWN"),
        "mission_name": header.get("MISSION_NAME", "LUNAR RECONNAISSANCE ORBITER"),
        "instrument_name": header.get("INSTRUMENT_NAME", "LROC NAC"),
        "orbit_number": header.get("ORBIT_NUMBER", "N/A"),
        "start_time": header.get("START_TIME", "N/A"),
    }
    
    return norm_img, metadata


def read_img(
    file_path: str,
    max_dim: Optional[int] = None,
    normalize_contrast: bool = True
) -> Tuple[np.ndarray, Dict[str, Any]]:
    """
    Primary interface for reading any .IMG file.
    Supports PDS3 lunar orbiter files, raw binary imagery, and standard formats.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"IMG file not found: {file_path}")

    # First check if this is a PDS3 image by inspecting the first 512 bytes
    try:
        with open(file_path, "rb") as f:
            header_sample = f.read(512).decode("latin1", errors="ignore")
            if "PDS_VERSION_ID" in header_sample or "RECORD_BYTES" in header_sample:
                return read_pds3_img(file_path, max_dim=max_dim, normalize_contrast=normalize_contrast)
    except Exception:
        pass

    # Second check: OpenCV standard image decode
    try:
        cv_img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
        if cv_img is not None:
            metadata = {
                "format": "STANDARD_IMG",
                "source_file": file_path,
                "original_dimensions": cv_img.shape,
                "output_dimensions": cv_img.shape,
                "dtype": str(cv_img.dtype)
            }
            return cv_img, metadata
    except Exception:
        pass

    # Third check: Detached PDS3 label (.lbl) in same folder
    base, _ = os.path.splitext(file_path)
    for ext in [".LBL", ".lbl"]:
        if os.path.exists(base + ext):
            return read_pds3_img(file_path, max_dim=max_dim, normalize_contrast=normalize_contrast)

    # Fourth fallback: Raw binary estimation based on file size
    file_size = os.path.getsize(file_path)
    dim = int(np.sqrt(file_size))
    if dim * dim == file_size:
        # Perfect square raw 8-bit image
        arr = np.memmap(file_path, dtype=np.uint8, mode="r", shape=(dim, dim))
        out_arr = np.array(arr)
        metadata = {
            "format": "RAW_BINARY_SQUARE",
            "source_file": file_path,
            "original_dimensions": (dim, dim),
            "output_dimensions": out_arr.shape
        }
        return out_arr, metadata

    # Final attempt with read_pds3_img parser
    try:
        return read_pds3_img(file_path, max_dim=max_dim, normalize_contrast=normalize_contrast)
    except Exception as e:
        raise ValueError(
            f"Unable to parse scientific IMG file: {file_path}. Details: {e}"
        )


def extract_img_preview(file_path: str, preview_out_path: str, max_dim: int = 1024) -> str:
    """
    Generates a web-displayable JPEG/PNG thumbnail preview for a large scientific IMG file.
    """
    img_data, meta = read_img(file_path, max_dim=max_dim, normalize_contrast=True)
    
    # If 1-channel grayscale, convert to 3-channel BGR for crisp JPEG/PNG output
    if len(img_data.shape) == 2:
        img_bgr = cv2.cvtColor(img_data, cv2.COLOR_GRAY2BGR)
    elif len(img_data.shape) == 3 and img_data.shape[2] == 1:
        img_bgr = cv2.cvtColor(img_data[:, :, 0], cv2.COLOR_GRAY2BGR)
    else:
        img_bgr = img_data

    # Ensure output directory exists
    os.makedirs(os.path.dirname(os.path.abspath(preview_out_path)), exist_ok=True)
    cv2.imwrite(preview_out_path, img_bgr)
    return preview_out_path
