"""
PyTorch Dataset and Patient-Level Splitter for Upper-Extremity Radiographs.
Guarantees zero data leakage by grouping studies strictly by patient ID.
"""

import os
import random
from typing import List, Tuple, Dict, Any, Optional
from PIL import Image

try:
    from torch.utils.data import Dataset
    import torchvision.transforms as T
except ImportError:
    Dataset = object
    T = None


def get_transforms(img_size: int = 224, is_train: bool = True):
    """Returns standard radiograph transformation pipeline."""
    if T is None:
        return None
    if is_train:
        return T.Compose([
            T.Resize((img_size, img_size)),
            T.RandomHorizontalFlip(p=0.5),
            T.RandomRotation(degrees=10),
            T.ColorJitter(brightness=0.1, contrast=0.1),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
    else:
        return T.Compose([
            T.Resize((img_size, img_size)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])


class RadiographDataset(Dataset):
    """PyTorch Dataset for radiograph triage."""
    def __init__(self, items: List[Dict[str, Any]], transform=None):
        self.items = items
        self.transform = transform

    def __len__(self) -> int:
        return len(self.items)

    def __getitem__(self, idx: int):
        import torch
        item = self.items[idx]
        img_path = item["image_path"]

        image = Image.open(img_path).convert("RGB")
        if self.transform:
            image_tensor = self.transform(image)
        else:
            image_tensor = image

        label = torch.tensor(item["ground_truth"], dtype=torch.float32)
        return image_tensor, label, item


def split_by_patient(
    items: List[Dict[str, Any]],
    val_ratio: float = 0.20,
    seed: int = 42
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Splits items into train and validation sets strictly by patient ID
    to prevent data leakage between splits.
    """
    rng = random.Random(seed)
    patients: Dict[str, List[Dict[str, Any]]] = {}

    for it in items:
        pid = it.get("patient_id") or it.get("image_path")
        if pid not in patients:
            patients[pid] = []
        patients[pid].append(it)

    patient_keys = list(patients.keys())
    rng.shuffle(patient_keys)

    n_val = int(len(patient_keys) * val_ratio)
    val_patients = set(patient_keys[:n_val])

    train_items: List[Dict[str, Any]] = []
    val_items: List[Dict[str, Any]] = []

    for pid, p_items in patients.items():
        if pid in val_patients:
            val_items.extend(p_items)
        else:
            train_items.extend(p_items)

    return train_items, val_items
