"""
Neural network architectures for musculoskeletal fracture and abnormality triage.
Supports DenseNet-121, EfficientNet-B0, and ResNet-50 backbones with
verified target layers for Grad-CAM explainability.
"""

from typing import Tuple, Any, Optional

# Verified Grad-CAM target layer names across torchvision models
TARGET_LAYER_MAP = {
    "densenet121": "features.norm5",
    "efficientnet_b0": "features.8",
    "resnet50": "layer4",
}


def get_target_layer_name(model_name: str) -> str:
    """Returns the canonical final convolutional layer for Grad-CAM."""
    return TARGET_LAYER_MAP.get(model_name.lower(), "features.norm5")


def build_fracture_classifier(
    model_name: str = "densenet121",
    pretrained: bool = True,
    num_classes: int = 1,
    dropout_rate: float = 0.2
) -> Tuple[Any, Any]:
    """
    Constructs a PyTorch fracture classification model with an adapted head.
    Returns (model, target_conv_layer).
    """
    try:
        import torch
        import torch.nn as nn
        from torchvision import models
    except ImportError:
        raise ImportError(
            "PyTorch and torchvision are required to build CNN architectures. "
            "Please install via: pip install torch torchvision"
        )

    model_name = model_name.lower()

    if model_name == "densenet121":
        weights = models.DenseNet121_Weights.DEFAULT if pretrained else None
        model = models.densenet121(weights=weights)
        target_layer = model.features.norm5
        in_features = model.classifier.in_features
        model.classifier = nn.Sequential(
            nn.Dropout(p=dropout_rate),
            nn.Linear(in_features, num_classes)
        )

    elif model_name == "efficientnet_b0":
        weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
        model = models.efficientnet_b0(weights=weights)
        target_layer = model.features[8]
        in_features = model.classifier[1].in_features
        model.classifier = nn.Sequential(
            nn.Dropout(p=dropout_rate),
            nn.Linear(in_features, num_classes)
        )

    elif model_name == "resnet50":
        weights = models.ResNet50_Weights.DEFAULT if pretrained else None
        model = models.resnet50(weights=weights)
        target_layer = model.layer4[-1]
        in_features = model.fc.in_features
        model.fc = nn.Sequential(
            nn.Dropout(p=dropout_rate),
            nn.Linear(in_features, num_classes)
        )

    else:
        raise ValueError(f"Unsupported model architecture: {model_name}. Use densenet121, efficientnet_b0, or resnet50.")

    return model, target_layer
