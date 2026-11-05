"""
Dataset loaders and manifest generators for Verifact evaluation.
Supports MURA (abnormality detection), FracAtlas (fracture detection),
and synthetic dry-run mock datasets.
"""

import os
import json
import random
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw


UPPER_EXTREMITY_PARTS = [
    "XR_WRIST", "XR_HAND", "XR_FOREARM", "XR_ELBOW",
    "XR_SHOULDER", "XR_HUMERUS", "XR_FINGER",
    "wrist", "hand", "forearm", "elbow", "shoulder", "humerus", "finger", "clavicle"
]


class DatasetItem:
    def __init__(
        self,
        image_path: str,
        ground_truth: int,
        task: str,
        body_part: str = "upper_extremity",
        patient_id: Optional[str] = None,
        study_id: Optional[str] = None
    ):
        self.image_path = image_path
        self.ground_truth = int(ground_truth)
        self.task = task  # "abnormality_detection" for MURA, "fracture_detection" for FracAtlas
        self.body_part = body_part
        self.patient_id = patient_id or "unknown"
        self.study_id = study_id or "unknown"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_path": self.image_path,
            "ground_truth": self.ground_truth,
            "task": self.task,
            "body_part": self.body_part,
            "patient_id": self.patient_id,
            "study_id": self.study_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DatasetItem":
        return cls(
            image_path=data["image_path"],
            ground_truth=data["ground_truth"],
            task=data.get("task", "fracture_detection"),
            body_part=data.get("body_part", "upper_extremity"),
            patient_id=data.get("patient_id"),
            study_id=data.get("study_id"),
        )


def load_mura_dataset(
    mura_dir: str,
    split: str = "valid",
    upper_extremity_only: bool = True
) -> List[DatasetItem]:
    """
    Loads MURA dataset items.
    MURA is evaluated as 'abnormality_detection'.
    split: 'train' or 'valid'. MURA's valid set is recommended as held-out test.
    """
    base_path = Path(mura_dir)
    items: List[DatasetItem] = []

    # Check for CSV file first
    csv_candidates = [
        base_path / f"{split}_image_paths.csv",
        base_path / f"{split}_labeled_studies.csv",
        base_path / f"{split}.csv"
    ]

    csv_found = False
    for csv_file in csv_candidates:
        if csv_file.exists():
            csv_found = True
            with open(csv_file, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(",")
                    if not parts or not parts[0]:
                        continue
                    img_rel = parts[0]
                    # Format: MURA-v1.1/valid/XR_WRIST/patient11184/study1_positive/image1.png
                    full_img_path = str(base_path / img_rel) if not os.path.isabs(img_rel) else img_rel
                    
                    body_part = "upper_extremity"
                    for part in UPPER_EXTREMITY_PARTS:
                        if part.lower() in img_rel.lower():
                            body_part = part
                            break

                    if upper_extremity_only and body_part == "upper_extremity":
                        continue

                    label = 1 if "positive" in img_rel.lower() else 0
                    if len(parts) > 1 and parts[1].strip() in ["0", "1"]:
                        label = int(parts[1].strip())

                    # Extract patient id
                    patient_id = "unknown"
                    for segment in img_rel.replace("\\", "/").split("/"):
                        if segment.startswith("patient"):
                            patient_id = segment
                            break

                    items.append(DatasetItem(
                        image_path=full_img_path,
                        ground_truth=label,
                        task="abnormality_detection",
                        body_part=body_part,
                        patient_id=patient_id
                    ))
            break

    # If CSV not found, traverse directory tree
    if not csv_found and base_path.exists():
        split_dir = base_path / split if (base_path / split).exists() else base_path
        for img_path in split_dir.glob("**/*.*"):
            if img_path.suffix.lower() not in [".png", ".jpg", ".jpeg", ".dcm"]:
                continue
            path_str = str(img_path)
            path_lower = path_str.lower().replace("\\", "/")

            body_part = "upper_extremity"
            for part in UPPER_EXTREMITY_PARTS:
                if part.lower() in path_lower:
                    body_part = part
                    break

            if upper_extremity_only and body_part == "upper_extremity":
                continue

            label = 1 if "positive" in path_lower else 0

            patient_id = "unknown"
            for segment in path_lower.split("/"):
                if "patient" in segment:
                    patient_id = segment
                    break

            items.append(DatasetItem(
                image_path=path_str,
                ground_truth=label,
                task="abnormality_detection",
                body_part=body_part,
                patient_id=patient_id
            ))

    return items


def load_fracatlas_dataset(
    fracatlas_dir: str,
    upper_extremity_only: bool = True
) -> List[DatasetItem]:
    """
    Loads FracAtlas dataset items.
    FracAtlas is evaluated as 'fracture_detection'.
    """
    base_path = Path(fracatlas_dir)
    items: List[DatasetItem] = []

    # Check for metadata CSV
    csv_candidates = [
        base_path / "dataset.csv",
        base_path / "FracAtlas" / "dataset.csv",
        base_path / "metadata.csv"
    ]

    for csv_file in csv_candidates:
        if csv_file.exists():
            import csv
            with open(csv_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Look for image filename/path
                    img_name = row.get("image_id") or row.get("image") or row.get("filename")
                    if not img_name:
                        continue
                    if not img_name.lower().endswith((".png", ".jpg", ".jpeg")):
                        img_name = f"{img_name}.png"

                    # Look for ground truth
                    fractured_val = row.get("fractured", row.get("fracture", row.get("label", "0")))
                    label = 1 if str(fractured_val).strip() in ["1", "true", "True", "positive"] else 0

                    body_part = str(row.get("body_part", row.get("organ", "upper_extremity"))).lower()
                    if upper_extremity_only:
                        matches = any(p.lower() in body_part for p in UPPER_EXTREMITY_PARTS)
                        if not matches:
                            continue

                    # Search possible image locations
                    possible_paths = [
                        base_path / "images" / ("Fractured" if label == 1 else "Non_fractured") / img_name,
                        base_path / "images" / img_name,
                        base_path / img_name
                    ]
                    actual_path = next((p for p in possible_paths if p.exists()), possible_paths[0])

                    items.append(DatasetItem(
                        image_path=str(actual_path),
                        ground_truth=label,
                        task="fracture_detection",
                        body_part=body_part,
                        patient_id=str(row.get("patient_id", row.get("id", "unknown")))
                    ))
            if items:
                return items

    # Fallback to directory structure
    if base_path.exists():
        seen_images = set()
        visited_folders = set()
        for sub_name, label in [("Fractured", 1), ("Non_fractured", 0), ("fractured", 1), ("normal", 0)]:
            folder = base_path / sub_name
            if not folder.exists():
                folder = base_path / "images" / sub_name
            if folder.exists():
                norm_folder = str(folder.resolve()).lower()
                if norm_folder in visited_folders:
                    continue
                visited_folders.add(norm_folder)

                for img_path in folder.glob("*.*"):
                    if img_path.suffix.lower() in [".png", ".jpg", ".jpeg", ".dcm"]:
                        img_key = str(img_path.resolve()).lower()
                        if img_key in seen_images:
                            continue
                        seen_images.add(img_key)
                        items.append(DatasetItem(
                            image_path=str(img_path),
                            ground_truth=label,
                            task="fracture_detection",
                            body_part="upper_extremity"
                        ))

    return items


def create_or_load_subset_manifest(
    items: List[DatasetItem],
    output_manifest_path: str,
    n_samples: int = 250,
    seed: int = 42
) -> List[DatasetItem]:
    """
    Creates or loads a fixed, seeded subset manifest saved to disk for exact reproducibility.
    Balances positive and negative cases as evenly as possible.
    """
    manifest_file = Path(output_manifest_path)
    if manifest_file.exists():
        with open(manifest_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            return [DatasetItem.from_dict(d) for d in data]

    rng = random.Random(seed)
    positives = [it for it in items if it.ground_truth == 1]
    negatives = [it for it in items if it.ground_truth == 0]

    n_pos = min(len(positives), n_samples // 2)
    n_neg = min(len(negatives), n_samples - n_pos)

    # Patient-level grouping if patient_id is available
    rng.shuffle(positives)
    rng.shuffle(negatives)

    selected = positives[:n_pos] + negatives[:n_neg]
    rng.shuffle(selected)

    manifest_file.parent.mkdir(parents=True, exist_ok=True)
    with open(manifest_file, "w", encoding="utf-8") as f:
        json.dump([it.to_dict() for it in selected], f, indent=2)

    return selected


def create_mock_test_dataset(
    target_dir: str,
    num_samples: int = 20
) -> List[DatasetItem]:
    """
    Generates a tiny synthetic dataset of mock radiographs (upper extremity)
    for dry-running the evaluation harness and CI testing without needing multi-GB downloads.
    """
    target_path = Path(target_dir)
    target_path.mkdir(parents=True, exist_ok=True)

    items: List[DatasetItem] = []
    body_parts = ["wrist", "hand", "forearm", "elbow"]

    for i in range(num_samples):
        label = 1 if i % 2 == 0 else 0
        part = body_parts[i % len(body_parts)]
        filename = f"mock_{part}_{'abnormal' if label else 'normal'}_{i:03d}.png"
        img_path = target_path / filename

        # Create dummy bone X-ray texture
        img = Image.new("L", (256, 256), color=20)
        draw = ImageDraw.Draw(img)

        # Draw bone-like shapes
        draw.rounded_rectangle([70, 30, 110, 220], radius=15, fill=160, outline=200)
        draw.rounded_rectangle([130, 30, 170, 220], radius=15, fill=170, outline=210)

        # If abnormal/fracture, draw a fracture line / discontinuity
        if label == 1:
            draw.line([65, 120, 115, 130], fill=30, width=3)

        img.save(img_path)

        items.append(DatasetItem(
            image_path=str(img_path),
            ground_truth=label,
            task="fracture_detection",
            body_part=part,
            patient_id=f"patient_mock_{i // 2:03d}",
            study_id=f"study_mock_{i:03d}"
        ))

    manifest_path = target_path / "mock_manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump([it.to_dict() for it in items], f, indent=2)

    return items
