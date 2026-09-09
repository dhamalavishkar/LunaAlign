import os
import cv2
import numpy as np
from typing import Tuple, Dict, Any, Optional

from src.data.io.format_detection import detect_format

class DataLoader:
    """
    Main interface for ingesting scientific and standard images.
    Automatically routes to the appropriate format handler based on file type.
    """
    def __init__(self):
        pass
        
    def load_image(self, file_path: str, max_dim: Optional[int] = None) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Loads an image from the given path, returning the image array and metadata.
        Supports optional max_dim for memory-efficient handling of large planetary datasets.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Image file not found: {file_path}")
            
        fmt = detect_format(file_path)
        
        if fmt == 'FITS':
            from src.data.io.format_handlers.fits_reader import read_fits
            return read_fits(file_path)
            
        elif fmt == 'PDS':
            from src.data.io.format_handlers.pds_reader import read_pds
            return read_pds(file_path)
            
        elif fmt == 'IMG':
            from src.data.io.format_handlers.img_reader import read_img
            return read_img(file_path, max_dim=max_dim)
            
        elif fmt == 'STANDARD':
            img = cv2.imread(file_path, cv2.IMREAD_UNCHANGED)
            if img is None:
                raise ValueError(f"OpenCV failed to read standard image: {file_path}")
            
            if max_dim is not None and max(img.shape[:2]) > max_dim:
                scale = max_dim / max(img.shape[:2])
                new_w = int(img.shape[1] * scale)
                new_h = int(img.shape[0] * scale)
                img = cv2.resize(img, (new_w, new_h), interpolation=cv2.INTER_AREA)

            metadata = {
                "format": "STANDARD",
                "dimensions": img.shape,
                "dtype": str(img.dtype)
            }
            return img.astype(np.float32), metadata
            
        else:
            # Fallback: try read_img anyway in case it's an unlabelled scientific binary
            try:
                from src.data.io.format_handlers.img_reader import read_img
                return read_img(file_path, max_dim=max_dim)
            except Exception:
                raise ValueError(f"Unsupported or unknown file format for file: {file_path}")

if __name__ == "__main__":
    loader = DataLoader()
    print("DataLoader successfully instantiated.")
