import io
from typing import Tuple, Dict, Any, Optional, List
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


def _extract_pixel_spacing(ds) -> Optional[List[float]]:
    """Reads standard DICOM PixelSpacing or ImagerPixelSpacing tags."""
    for tag_name in ("PixelSpacing", "ImagerPixelSpacing", "NominalScannedPixelSpacing"):
        val = getattr(ds, tag_name, None)
        if val:
            try:
                if isinstance(val, (list, tuple, pydicom.multival.MultiValue)) and len(val) >= 2:
                    return [float(val[0]), float(val[1])]
            except Exception:
                pass
    return None


def process_dicom_bytes(file_bytes: bytes) -> Tuple[bytes, Dict[str, Any]]:
    """
    Parses a raw DICOM byte stream:
    - Extracts patient & study metadata tags.
    - Extracts true PixelSpacing / ImagerPixelSpacing for caliper calibration.
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
            p2, p98 = np.percentile(pixel_array, (1, 99))
            pixel_array = np.clip(pixel_array, p2, p98)
            pixel_array = ((pixel_array - p2) / max(p98 - p2, 1e-5)) * 255.0
    else:
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

    # Convert to 3-channel RGB for display & processing
    if len(pixel_uint8.shape) == 2:
        img_rgb = cv2.cvtColor(pixel_uint8, cv2.COLOR_GRAY2RGB)
    else:
        img_rgb = pixel_uint8

    pil_img = Image.fromarray(img_rgb)
    out_buffer = io.BytesIO()
    pil_img.save(out_buffer, format="PNG", optimize=True)
    png_bytes = out_buffer.getvalue()

    spacing = _extract_pixel_spacing(ds)

    # Extract metadata tags
    metadata = {
        "is_dicom": True,
        "modality": str(getattr(ds, "Modality", "DX")),
        "body_part_examined": str(getattr(ds, "BodyPartExamined", "") or ""),
        "view_position": str(getattr(ds, "ViewPosition", "") or ""),
        "patient_id": str(getattr(ds, "PatientID", "ANONYMOUS")),
        "patient_name": str(getattr(ds, "PatientName", "") or ""),
        "study_description": str(getattr(ds, "StudyDescription", "") or ""),
        "photometric_interpretation": str(photometric),
        "window_center": float(window_center) if window_center is not None else None,
        "window_width": float(window_width) if window_width is not None else None,
        "rows": int(getattr(ds, "Rows", img_rgb.shape[0])),
        "columns": int(getattr(ds, "Columns", img_rgb.shape[1])),
        "pixel_spacing": spacing,
    }

    return png_bytes, metadata


def deidentify_dicom_metadata(metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Strips Protected Health Information (PHI) before any metadata is sent to an external LLM/Vision API.
    Guarantees that PatientName, PatientID, birth date, institution, or physician names are never dispatched.
    """
    if not metadata:
        return {}

    sanitized = {
        "is_dicom": metadata.get("is_dicom", False),
        "modality": metadata.get("modality", "DX"),
        "body_part_examined": metadata.get("body_part_examined", ""),
        "view_position": metadata.get("view_position", ""),
        "pixel_spacing": metadata.get("pixel_spacing"),
        "rows": metadata.get("rows"),
        "columns": metadata.get("columns"),
        # PHI explicitly stripped/redacted
        "patient_id": "[DE-IDENTIFIED]",
        "patient_name": "[DE-IDENTIFIED]",
    }
    return sanitized


def sanitize_image_pixels_for_external_api(image_bytes: bytes) -> Tuple[bytes, bool]:
    """
    Inspects image margins (top 7% of radiograph) for burned-in hospital text annotations.
    If high-contrast text is detected, masks that strip to black before transmitting
    to external multimodal cloud APIs. Returns (sanitized_bytes, text_masked_flag).
    """
    try:
        np_arr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if img is None:
            return image_bytes, False

        h, w, _ = img.shape
        margin_h = max(int(h * 0.07), 24)

        # Top strip where burned-in patient names typically appear
        top_strip = img[0:margin_h, :]
        gray_strip = cv2.cvtColor(top_strip, cv2.COLOR_BGR2GRAY)

        # Check for bright text on dark background or sharp edge clusters
        edges = cv2.Canny(gray_strip, 80, 200)
        edge_density = float(np.sum(edges > 0)) / float(margin_h * w)

        text_detected = False
        if edge_density > 0.035 or (float(np.max(gray_strip)) > 240 and float(np.min(gray_strip)) < 20):
            # Mask the top banner with pure black
            img[0:margin_h, :] = 0
            text_detected = True
            print(f"[DE-IDENTIFICATION] Burned-in text annotation detected in image margin (density: {edge_density:.4f}); masked prior to external API dispatch.")

        if text_detected:
            success, buffer = cv2.imencode(".png", img)
            if success:
                return buffer.tobytes(), True

        return image_bytes, False
    except Exception as exc:
        print(f"[WARN] Failed pixel sanitization check ({exc}); forwarding original.")
        return image_bytes, False
