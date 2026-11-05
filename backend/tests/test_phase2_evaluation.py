"""
Unit tests for Phase 2: Verifact Evaluation Harness.
Tests metric calculations, dataset loaders, manifest reproducibility, and benchmark runner.
"""

import os
import json
import tempfile
import pytest
from pathlib import Path
from PIL import Image

from evaluation.metrics import (
    compute_confusion_matrix,
    compute_expected_calibration_error,
    compute_brier_score,
    compute_clinical_metrics
)
from evaluation.dataset_loaders import (
    DatasetItem,
    load_mura_dataset,
    load_fracatlas_dataset,
    create_or_load_subset_manifest,
    create_mock_test_dataset
)
from evaluation.runner import evaluate_dataset


def test_metrics_calculation():
    # 10 positive cases, 10 negative cases
    # Predictions:
    # 8 TP, 2 FN (out of 10 positives => sens = 0.8)
    # 7 TN, 3 FP (out of 10 negatives => spec = 0.7)
    y_true = [1] * 10 + [0] * 10
    y_pred = [1] * 8 + [0] * 2 + [1] * 3 + [0] * 7
    y_prob = [0.9] * 8 + [0.3] * 2 + [0.8] * 3 + [0.1] * 7
    latencies = [15.0, 20.0, 25.0, 30.0]

    metrics = compute_clinical_metrics(
        y_true=y_true,
        y_pred=y_pred,
        y_prob=y_prob,
        latencies_ms=latencies
    )

    assert metrics["confusion_matrix"]["tp"] == 8
    assert metrics["confusion_matrix"]["fn"] == 2
    assert metrics["confusion_matrix"]["fp"] == 3
    assert metrics["confusion_matrix"]["tn"] == 7
    assert metrics["sensitivity_recall"] == 0.8
    assert metrics["specificity"] == 0.7
    assert metrics["precision_ppv"] == round(8 / 11, 4)
    assert metrics["auroc"] is not None
    assert metrics["auroc"] > 0.80  # Good separation
    assert metrics["expected_calibration_error_ece"] is not None
    assert metrics["brier_score"] is not None
    assert metrics["latency"]["mean_ms"] == 22.5


def test_dataset_item_serialization():
    item = DatasetItem(
        image_path="/tmp/img.png",
        ground_truth=1,
        task="fracture_detection",
        body_part="wrist",
        patient_id="pt123"
    )
    d = item.to_dict()
    assert d["ground_truth"] == 1
    assert d["task"] == "fracture_detection"
    assert d["patient_id"] == "pt123"

    restored = DatasetItem.from_dict(d)
    assert restored.image_path == item.image_path
    assert restored.ground_truth == 1


def test_mock_dataset_generator():
    with tempfile.TemporaryDirectory() as tmp_dir:
        items = create_mock_test_dataset(tmp_dir, num_samples=6)
        assert len(items) == 6
        for item in items:
            assert os.path.exists(item.image_path)
            assert item.ground_truth in [0, 1]
            assert item.task == "fracture_detection"

        manifest_file = os.path.join(tmp_dir, "mock_manifest.json")
        assert os.path.exists(manifest_file)


def test_subset_manifest_reproducibility():
    with tempfile.TemporaryDirectory() as tmp_dir:
        items = create_mock_test_dataset(tmp_dir, num_samples=10)
        manifest_path = os.path.join(tmp_dir, "manifest_seeded.json")

        # Create first time with seed 42
        subset1 = create_or_load_subset_manifest(items, manifest_path, n_samples=4, seed=42)
        assert len(subset1) == 4

        # Read back from disk
        subset2 = create_or_load_subset_manifest(items, manifest_path, n_samples=4, seed=42)
        assert len(subset2) == 4
        assert [x.image_path for x in subset1] == [x.image_path for x in subset2]


def test_mura_directory_parsing_structure():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Construct mock MURA directory hierarchy:
        # valid/XR_WRIST/patient001/study1_positive/image1.png
        # valid/XR_WRIST/patient002/study1_negative/image2.png
        wrist_pos = Path(tmp_dir) / "valid" / "XR_WRIST" / "patient001" / "study1_positive"
        wrist_neg = Path(tmp_dir) / "valid" / "XR_WRIST" / "patient002" / "study1_negative"
        wrist_pos.mkdir(parents=True)
        wrist_neg.mkdir(parents=True)

        img = Image.new("L", (10, 10), color=50)
        img.save(wrist_pos / "image1.png")
        img.save(wrist_neg / "image2.png")

        items = load_mura_dataset(tmp_dir, split="valid")
        assert len(items) == 2
        pos = next(i for i in items if i.ground_truth == 1)
        neg = next(i for i in items if i.ground_truth == 0)

        assert pos.task == "abnormality_detection"
        assert neg.task == "abnormality_detection"
        assert "XR_WRIST" in pos.body_part
        assert "patient001" in pos.patient_id


def test_fracatlas_directory_parsing_structure():
    with tempfile.TemporaryDirectory() as tmp_dir:
        # Construct mock FracAtlas directory hierarchy:
        # images/Fractured/fracture_wrist_01.png
        # images/Non_fractured/normal_wrist_02.png
        frac_dir = Path(tmp_dir) / "images" / "Fractured"
        norm_dir = Path(tmp_dir) / "images" / "Non_fractured"
        frac_dir.mkdir(parents=True)
        norm_dir.mkdir(parents=True)

        img = Image.new("L", (10, 10), color=50)
        img.save(frac_dir / "fracture_wrist_01.png")
        img.save(norm_dir / "normal_wrist_02.png")

        items = load_fracatlas_dataset(tmp_dir)
        assert len(items) == 2
        pos = next(i for i in items if i.ground_truth == 1)
        neg = next(i for i in items if i.ground_truth == 0)

        assert pos.task == "fracture_detection"
        assert neg.task == "fracture_detection"


def test_evaluate_dataset_mock_end_to_end():
    with tempfile.TemporaryDirectory() as tmp_dir:
        mock_dir = os.path.join(tmp_dir, "data")
        results_dir = os.path.join(tmp_dir, "results")
        items = create_mock_test_dataset(mock_dir, num_samples=8)

        res = evaluate_dataset(
            items=items,
            provider="mock",
            output_dir=results_dir,
            dataset_name="mock_test"
        )

        assert res["benchmark_metadata"]["dataset"] == "mock_test"
        assert res["benchmark_metadata"]["total_samples"] == 8
        assert "metrics" in res
        assert "sensitivity_recall" in res["metrics"]
        assert "f1_score" in res["metrics"]

        # Verify summary.md exists and contains header
        summary_file = Path(results_dir) / "summary.md"
        assert summary_file.exists()
        summary_text = summary_file.read_text(encoding="utf-8")
        assert "# Verifact Evaluation Benchmark Results" in summary_text
        assert "mock_test" in summary_text
