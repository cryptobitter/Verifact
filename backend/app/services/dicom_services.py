import io
from typing import Tuple, Dict, Any, Optional
import numpy as np
from PIL import Image
import cv2

try:
    import pydicom
    from pydicom.dataset import FileDataset
except ImportError:
    pydicom = None


def is_dicom_file(file_bytes: bytes, filename: Optional[str] = None) -> bool:
    """Checks whether the given bytes or filename represent a DICOM file."""
    if filename:
        ext = filename.lower().split(".")[-1]
        if ext in ("dcm", "dicom"):
            return True

    if len(file_bytes) > 132 and file_bytes[128:132] == b"DICM":
        return True

    if pydicom:
        try:
            pydicom.dcmread(io.BytesIO(file_bytes), stop_before_pixels=True, force=False)
            return True
        except Exception:
            pass

    return False


def process_dicom_bytes(file_bytes: bytes) -> Tuple[bytes, Dict[str, Any]]:
    """
    Parses a raw DICOM byte stream:
    - Extracts patient & study metadata tags.
    - Applies Window Width (WW) and Window Center (WC) / VOI LUT.
    - Corrects for MONOCHROME1 vs MONOCHROME2 photometric interpretation.
    - Converts the 12/16-bit radiograph into a normalized 8-bit RGB PNG byte stream.
    """
    if not pydicom:
        raise RuntimeError("pydicom is not installed. Please install pydicom to handle DICOM files.")

    try:
        ds: FileDataset = pydicom.dcmread(io.BytesIO(file_bytes), force=True)
    except Exception as exc:
        raise ValueError(f"Failed to parse DICOM dataset: {exc}") from exc

    try:
        pixel_array = ds.pixel_array.astype(np.float32)
    except Exception as exc:
        raise ValueError(f"Failed to read pixel data from DICOM file: {exc}") from exc

    # Rescale slope and intercept (HU or optical density transformation)
    rescale_slope = getattr(ds, "RescaleSlope", 1.0)
    rescale_intercept = getattr(ds, "RescaleIntercept", 0.0)
    if rescale_slope is not None and rescale_intercept is not None:
        try:
            pixel_array = pixel_array * float(rescale_slope) + float(rescale_intercept)
        except Exception:
            pass

    # Window Center & Window Width processing
    window_center = getattr(ds, "WindowCenter", None)
    window_width = getattr(ds, "WindowWidth", None)

    # Sometimes WW/WC can be multi-valued (DSlist)
    if isinstance(window_center, (list, pydicom.multival.MultiValue)):
        window_center = window_center[0]
    if isinstance(window_width, (list, pydicom.multival.MultiValue)):
        window_width = window_width[0]

    if window_center is not None and window_width is not None:
        try:
            wc = float(window_center)
            ww = float(window_width)
            c_min = wc - (ww / 2.0)
            c_max = wc + (ww / 2.0)
            pixel_array = np.clip(pixel_array, c_min, c_max)
            pixel_array = ((pixel_array - c_min) / max(ww, 1e-5)) * 255.0
        except Exception:
            # Fallback to percentile dynamic range
            p2, p98 = np.percentile(pixel_array, (1, 99))
            pixel_array = np.clip(pixel_array, p2, p98)
            pixel_array = ((pixel_array - p2) / max(p98 - p2, 1e-5)) * 255.0
    else:
        # Auto-windowing based on min-max
        p_min, p_max = float(np.min(pixel_array)), float(np.max(pixel_array))
        if p_max > p_min:
            pixel_array = ((pixel_array - p_min) / (p_max - p_min)) * 255.0
        else:
            pixel_array = np.zeros_like(pixel_array)

    pixel_uint8 = np.uint8(np.clip(pixel_array, 0, 255))

    # Invert if MONOCHROME1 (0 is maximum brightness/white, 255 is black)
    photometric = getattr(ds, "PhotometricInterpretation", "MONOCHROME2")
    if str(photometric).strip().upper() == "MONOCHROME1":
        pixel_uint8 = 255 - pixel_uint8

    # Convert to 3-channel BGR/RGB for ML pipeline and standard browser display
    if len(pixel_uint8.shape) == 2:
        img_rgb = cv2.cvtColor(pixel_uint8, cv2.COLOR_GRAY2RGB)
    else:
        img_rgb = pixel_uint8

    pil_img = Image.fromarray(img_rgb)
    out_buffer = io.BytesIO()
    pil_img.save(out_buffer, format="PNG", optimize=True)
    png_bytes = out_buffer.getvalue()

    # Extract metadata tags
    metadata = {
        "is_dicom": True,
        "modality": str(getattr(ds, "Modality", "DX")),
        "body_part_examined": str(getattr(ds, "BodyPartExamined", "") or ""),
        "view_position": str(getattr(ds, "ViewPosition", "") or ""),
        "patient_id": str(getattr(ds, "PatientID", "ANONYMOUS")),
        "study_description": str(getattr(ds, "StudyDescription", "") or ""),
        "photometric_interpretation": str(photometric),
        "window_center": float(window_center) if window_center is not None else None,
        "window_width": float(window_width) if window_width is not None else None,
        "rows": int(getattr(ds, "Rows", img_rgb.shape[0])),
        "columns": int(getattr(ds, "Columns", img_rgb.shape[1])),
    }

    return png_bytes, metadata
