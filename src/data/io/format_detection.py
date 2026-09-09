import os

def detect_format(file_path: str) -> str:
    """
    Detects the scientific or standard image format based on file extension and header.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    ext = os.path.splitext(file_path)[1].lower()
    
    if ext in ['.fits', '.fit']:
        return 'FITS'
    elif ext in ['.lbl', '.xml']:
        return 'PDS'
    elif ext in ['.img', '.bin', '.dat', '.raw']:
        return 'IMG'
    elif ext in ['.png', '.jpg', '.jpeg', '.tif', '.tiff', '.bmp']:
        return 'STANDARD'
        
    # Inspect header bytes if extension is unrecognized
    try:
        with open(file_path, 'rb') as f:
            sample = f.read(512).decode('latin1', errors='ignore')
            if 'PDS_VERSION_ID' in sample or 'RECORD_BYTES' in sample:
                return 'IMG'
            if 'SIMPLE  =' in sample:
                return 'FITS'
    except Exception:
        pass

    return 'UNKNOWN'
