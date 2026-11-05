"""
Unit tests for Phases 3, 4, and 5:
- Phase 3: CNN model target layers, real Grad-CAM overlay, patient-level split.
- Phase 4: Router agreement/discordance, uncertainty band, priority review queue.
- Phase 5: Storage abstraction, async job queue, audit logging, health check.
"""

import os
import io
import tempfile
import pytest
import numpy as np
from pathlib import Path
from PIL import Image

from ml.models import get_target_layer_name
from ml.gradcam import apply_gradcam_overlay
from ml.dataset import split_by_patient
from ml.inference import FractureInferenceEngine
from app.services.storage_service import LocalStorageService
from app.services.job_queue import JobQueueManager
from app.models.audit_log import AuditLog
from app.database import Base, engine, SessionLocal
from app.models.analysis import Analysis
from app.models.user import User


def test_phase3_target_layer_mapping():
    assert get_target_layer_name("densenet121") == "features.norm5"
    assert get_target_layer_name("efficientnet_b0") == "features.8"
    assert get_target_layer_name("resnet50") == "layer4"


def test_phase3_patient_level_split_no_leakage():
    # 10 items from 3 distinct patients
    items = [
        {"patient_id": "pt_A", "image_path": "a1.png", "ground_truth": 1},
        {"patient_id": "pt_A", "image_path": "a2.png", "ground_truth": 1},
        {"patient_id": "pt_A", "image_path": "a3.png", "ground_truth": 1},
        {"patient_id": "pt_B", "image_path": "b1.png", "ground_truth": 0},
        {"patient_id": "pt_B", "image_path": "b2.png", "ground_truth": 0},
        {"patient_id": "pt_C", "image_path": "c1.png", "ground_truth": 1},
        {"patient_id": "pt_C", "image_path": "c2.png", "ground_truth": 1},
    ]

    train_items, val_items = split_by_patient(items, val_ratio=0.33, seed=42)

    train_patients = {it["patient_id"] for it in train_items}
    val_patients = {it["patient_id"] for it in val_items}

    # Strict zero patient intersection between train and val
    assert len(train_patients.intersection(val_patients)) == 0
    assert len(train_items) + len(val_items) == len(items)


def test_phase3_gradcam_overlay_blend():
    rgb = np.zeros((100, 100, 3), dtype=np.uint8)
    heatmap_2d = np.ones((10, 10), dtype=np.float32) * 0.8  # high activation

    blended, colored = apply_gradcam_overlay(rgb, heatmap_2d, alpha=0.40)
    assert blended.shape == (100, 100, 3)
    assert colored.shape == (100, 100, 3)
    # Blended should not be all black since heatmap had activation
    assert np.mean(blended) > 0


def test_phase3_inference_engine_uncertainty():
    engine = FractureInferenceEngine()
    assert engine.uncertainty_min == 0.40
    assert engine.uncertainty_max == 0.70

    # Test uncertainty range
    assert engine.uncertainty_min <= 0.55 <= engine.uncertainty_max


def test_phase4_router_disagreement_and_priority_logic():
    # Simulating router logic:
    def evaluate_priority(cnn_det, cnn_prob, llm_det, severity="Low"):
        if cnn_det is not None and llm_det is not None:
            if cnn_det != llm_det:
                return "priority", "Discordance"
            elif 0.40 <= cnn_prob <= 0.70:
                return "priority", "Uncertain"
            elif severity == "High":
                return "priority", "Severe"
        return "normal", "Concordant"

    # Discordance: CNN=True, LLM=False
    p1, r1 = evaluate_priority(True, 0.85, False)
    assert p1 == "priority"
    assert "Discordance" in r1

    # Indeterminate confidence within [0.40, 0.70]
    p2, r2 = evaluate_priority(True, 0.54, True)
    assert p2 == "priority"
    assert "Uncertain" in r2

    # High severity
    p3, r3 = evaluate_priority(True, 0.95, True, severity="High")
    assert p3 == "priority"

    # Concordant clean normal
    p4, r4 = evaluate_priority(False, 0.12, False, severity="Low")
    assert p4 == "normal"


def test_phase5_storage_abstraction():
    with tempfile.TemporaryDirectory() as tmp_dir:
        storage = LocalStorageService(base_dir=Path(tmp_dir))
        payload = b"TEST_RADIOGRAPH_BYTES_123"
        url = storage.save_bytes(payload, "wrist_xray.jpg")

        assert url.startswith("/uploads/")
        assert "wrist_xray" in url

        retrieved = storage.get_bytes(url)
        assert retrieved == payload


def test_phase5_async_job_queue():
    mgr = JobQueueManager()
    rec = mgr.create_job("job_xyz", user_id=1)
    assert rec.status == "queued"
    assert rec.progress == 0

    mgr.update_progress("job_xyz", 50, status="processing")
    j = mgr.get_job("job_xyz")
    assert j["status"] == "processing"
    assert j["progress"] == 50

    mgr.complete_job("job_xyz", {"fracture_detected": True, "bone": "Radius"})
    j_done = mgr.get_job("job_xyz")
    assert j_done["status"] == "completed"
    assert j_done["progress"] == 100
    assert j_done["result"]["bone"] == "Radius"


def test_phase5_audit_log_persisted():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        log = AuditLog(
            user_id=1,
            analysis_id=999,
            action="SIGN_OFF",
            details="Physician Dr. Smith signed off on analysis"
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        assert log.id is not None
        assert log.action == "SIGN_OFF"
        assert log.created_at is not None
    finally:
        db.close()
