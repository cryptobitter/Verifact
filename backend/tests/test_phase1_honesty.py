import pytest
import numpy as np
import cv2
import io
import shutil
from pathlib import Path
from PIL import Image

from app.services.ml_pipeline import _clinical_offline_enhancement_engine, _validate_and_sanitize_llm_dict
from app.services.dicom_services import deidentify_dicom_metadata, sanitize_image_pixels_for_external_api
from app.schemas.analysis_schema import ModelOutput, LlmStructuredOutput
import app.database as db_mod


def test_offline_mode_emits_no_fabricated_predictions():
    dummy_gray = np.zeros((200, 200), dtype=np.uint8)
    res = _clinical_offline_enhancement_engine(dummy_gray)

    # Hard honesty rules
    assert res["fracture_detected"] is None, "Offline mode must not emit a boolean fracture prediction"
    assert res["confidence"] is None, "Offline mode must not emit a confidence score"
    assert res["is_ai_analysis"] is False, "is_ai_analysis must be False in offline mode"
    assert res["analysis_mode"] == "offline_enhancement_only"
    assert "No AI analysis performed" in res["notice"]
    assert "No AI analysis performed" in res["report_text"]


def test_pydantic_llm_validation_valid():
    valid_payload = {
        "fracture_detected": True,
        "confidence": 0.85,
        "bone": "Distal Radius",
        "location": "Metaphysis",
        "fracture_type": "Transverse",
        "displacement": "Dorsally angulated",
        "severity": "Moderate",
        "roi_coordinates": {"x": 0.55, "y": 0.62}
    }
    validated = _validate_and_sanitize_llm_dict(valid_payload)
    assert validated is not None
    assert validated["fracture_detected"] is True
    assert validated["confidence"] == 0.85
    assert validated["roi_coordinates"] == {"x": 0.55, "y": 0.62}


def test_pydantic_llm_validation_clamps_out_of_bounds_roi():
    out_of_bounds_payload = {
        "fracture_detected": True,
        "confidence": 0.90,
        "bone": "Clavicle",
        "roi_coordinates": {"x": -0.25, "y": 1.45}
    }
    validated = _validate_and_sanitize_llm_dict(out_of_bounds_payload)
    assert validated is not None
    # Clamped to [0.05, 0.95]
    assert 0.05 <= validated["roi_coordinates"]["x"] <= 0.95
    assert 0.05 <= validated["roi_coordinates"]["y"] <= 0.95


def test_pydantic_llm_validation_rejects_malformed_confidence():
    invalid_confidence = {
        "fracture_detected": True,
        "confidence": 95.0,  # Invalid: must be <= 1.0
        "bone": "Ulna"
    }
    validated = _validate_and_sanitize_llm_dict(invalid_confidence)
    assert validated is None, "Should reject confidence > 1.0"


def test_dicom_deidentification_scrubs_phi():
    raw_metadata = {
        "is_dicom": True,
        "patient_name": "Doe^John",
        "patient_id": "MRN-99412-SECRET",
        "modality": "DX",
        "body_part_examined": "WRIST",
        "view_position": "AP",
        "pixel_spacing": [0.143, 0.143],
        "rows": 1024,
        "columns": 1024
    }

    clean = deidentify_dicom_metadata(raw_metadata)
    assert clean["patient_id"] == "[DE-IDENTIFIED]"
    assert clean["patient_name"] == "[DE-IDENTIFIED]"
    assert clean["body_part_examined"] == "WRIST"
    assert clean["pixel_spacing"] == [0.143, 0.143]


def test_burned_in_text_sanitizer():
    # Create image with bright burned-in text block in top margin
    img = np.zeros((300, 300, 3), dtype=np.uint8)
    cv2.putText(img, "PATIENT: DOE, JOHN 01/01/1980 HOSPITAL ID: 12345", (10, 15),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)

    _, png_bytes = cv2.imencode(".png", img)
    sanitized_bytes, text_masked = sanitize_image_pixels_for_external_api(png_bytes.tobytes())

    assert text_masked is True, "Should detect and mask high-contrast text in top strip"

    # Decode sanitized bytes and verify top margin has been blanked
    sanitized_np = cv2.imdecode(np.frombuffer(sanitized_bytes, np.uint8), cv2.IMREAD_COLOR)
    assert np.max(sanitized_np[0:15, :]) == 0, "Top margin must be blanked out to 0"


def test_database_migration_copies_without_deleting(tmp_path, monkeypatch):
    test_src = tmp_path / "fractoes.db"
    test_src.write_text("dummy database content")
    test_dst = tmp_path / "verifact.db"

    monkeypatch.setattr(db_mod, "DB_FILE_PATH", test_dst)
    monkeypatch.setattr(db_mod, "LEGACY_DB_PATH", test_src)
    monkeypatch.setattr(db_mod, "ROOT_LEGACY_DB_PATH", test_src)

    db_mod._migrate_legacy_db_if_needed()

    assert test_dst.exists(), "Target verifact.db must be created"
    assert test_dst.read_text() == "dummy database content"
    assert test_src.exists(), "Original legacy database must NEVER be deleted"
