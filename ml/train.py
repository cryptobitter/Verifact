"""
Training pipeline for fine-tuning CNNs on musculoskeletal radiographs.
Includes patient-level split to prevent data leakage, class imbalance weighting,
learning rate scheduling, AUROC validation, and checkpoint export.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ml.models import build_fracture_classifier, get_target_layer_name
from ml.dataset import RadiographDataset, get_transforms, split_by_patient
from evaluation.dataset_loaders import (
    load_mura_dataset,
    load_fracatlas_dataset,
    create_mock_test_dataset
)


def train_model(
    model_name: str = "densenet121",
    dataset_name: str = "mock",
    dataset_path: str = None,
    epochs: int = 5,
    batch_size: int = 16,
    lr: float = 1e-4,
    output_dir: str = "ml/checkpoints",
    cpu_debug: bool = False,
    n_debug_samples: int = 20
):
    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader
        from sklearn.metrics import roc_auc_score
    except ImportError as e:
        print(f"ERROR: Missing PyTorch or scikit-learn dependency: {e}")
        print("Please install requirements: pip install torch torchvision scikit-learn")
        sys.exit(1)

    device = torch.device("cuda" if torch.cuda.is_available() and not cpu_debug else "cpu")
    print(f"\nTraining Config: Model={model_name}, Dataset={dataset_name}, Device={device}, Epochs={epochs}")

    # Load dataset items
    if dataset_name == "mock" or cpu_debug:
        mock_dir = str(PROJECT_ROOT / "evaluation" / "mock_dataset")
        items = [it.to_dict() for it in create_mock_test_dataset(mock_dir, num_samples=n_debug_samples)]
    elif dataset_name == "mura":
        raw = load_mura_dataset(dataset_path or os.getenv("MURA_DATASET_PATH"), split="train")
        items = [it.to_dict() for it in raw]
    elif dataset_name == "fracatlas":
        raw = load_fracatlas_dataset(dataset_path or os.getenv("FRACATLAS_DATASET_PATH"))
        items = [it.to_dict() for it in raw]
    else:
        raise ValueError(f"Unknown dataset: {dataset_name}")

    train_items, val_items = split_by_patient(items, val_ratio=0.20, seed=42)
    print(f"Dataset split: Train={len(train_items)} samples, Val={len(val_items)} samples (patient-stratified)")

    # Datasets and Loaders
    train_dataset = RadiographDataset(train_items, transform=get_transforms(img_size=224, is_train=True))
    val_dataset = RadiographDataset(val_items, transform=get_transforms(img_size=224, is_train=False))

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, drop_last=False)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False)

    # Class imbalance handling
    n_pos = sum(1 for it in train_items if it["ground_truth"] == 1)
    n_neg = len(train_items) - n_pos
    pos_weight = torch.tensor([n_neg / max(1, n_pos)], dtype=torch.float32).to(device)
    print(f"Class imbalance pos_weight: {pos_weight.item():.2f} (pos={n_pos}, neg={n_neg})")

    # Build model
    model, target_layer = build_fracture_classifier(model_name=model_name, pretrained=True, num_classes=1)
    model = model.to(device)

    criterion = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optimizer = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=1e-2)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_loss = float("inf")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0

        for images, labels, _ in train_loader:
            images = images.to(device)
            labels = labels.to(device).unsqueeze(1)

            optimizer.zero_grad()
            logits = model(images)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()

            running_loss += loss.item() * images.size(0)

        scheduler.step()
        epoch_train_loss = running_loss / max(1, len(train_dataset))

        # Validation
        model.eval()
        val_loss = 0.0
        val_preds = []
        val_targets = []

        with torch.no_grad():
            for images, labels, _ in val_loader:
                images = images.to(device)
                labels = labels.to(device).unsqueeze(1)
                logits = model(images)
                loss = criterion(logits, labels)
                val_loss += loss.item() * images.size(0)

                probs = torch.sigmoid(logits).squeeze(1).cpu().numpy().tolist()
                targets = labels.squeeze(1).cpu().numpy().tolist()
                val_preds.extend(probs if isinstance(probs, list) else [probs])
                val_targets.extend(targets if isinstance(targets, list) else [targets])

        epoch_val_loss = val_loss / max(1, len(val_dataset))
        val_auroc = 0.50
        if len(set(val_targets)) > 1:
            try:
                val_auroc = roc_auc_score(val_targets, val_preds)
            except Exception:
                pass

        print(f"Epoch [{epoch}/{epochs}] - Train Loss: {epoch_train_loss:.4f} | Val Loss: {epoch_val_loss:.4f} | Val AUROC: {val_auroc:.4f}")

        # Checkpoint if best
        if epoch_val_loss < best_val_loss:
            best_val_loss = epoch_val_loss
            ckpt_file = out_path / f"{model_name}_best.pt"
            torch.save({
                "epoch": epoch,
                "model_name": model_name,
                "model_state_dict": model.state_dict(),
                "val_loss": epoch_val_loss,
                "val_auroc": val_auroc,
                "target_layer_name": get_target_layer_name(model_name),
                "config": {
                    "model_name": model_name,
                    "img_size": 224,
                    "num_classes": 1,
                    "pos_weight": pos_weight.item()
                }
            }, ckpt_file)

            # Write config JSON
            with open(out_path / "config.json", "w", encoding="utf-8") as f:
                json.dump({
                    "model_name": model_name,
                    "checkpoint_file": str(ckpt_file.name),
                    "best_val_loss": epoch_val_loss,
                    "best_val_auroc": val_auroc,
                    "target_layer_name": get_target_layer_name(model_name),
                    "img_size": 224
                }, f, indent=2)

    print(f"\nTraining completed. Best checkpoint saved to {out_path / f'{model_name}_best.pt'}")


def main():
    parser = argparse.ArgumentParser(description="Verifact CNN Fine-Tuning Pipeline")
    parser.add_argument("--model", default="densenet121", choices=["densenet121", "efficientnet_b0", "resnet50"])
    parser.add_argument("--dataset", default="mock", choices=["mura", "fracatlas", "mock"])
    parser.add_argument("--dataset-path", default=None)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--cpu-debug", action="store_true")
    parser.add_argument("--n-debug-samples", type=int, default=20)
    parser.add_argument("--output-dir", default="ml/checkpoints")
    args = parser.parse_args()

    train_model(
        model_name=args.model,
        dataset_name=args.dataset,
        dataset_path=args.dataset_path,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.lr,
        output_dir=args.output_dir,
        cpu_debug=args.cpu_debug,
        n_debug_samples=args.n_debug_samples
    )


if __name__ == "__main__":
    main()
