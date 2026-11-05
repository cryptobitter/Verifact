"""
Production Inference Module for Verifact CNN.
Loads fine-tuned checkpoints, runs forward inference, checks uncertainty bounds,
and generates real Grad-CAM heatmaps from the verified convolutional target layer.
"""

import os
import io
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union
import numpy as np
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
import cv2

PROJECT_ROOT = Path(__file__).resolve().parent.parent
from ml.models import build_fracture_classifier, get_target_layer_name
from ml.gradcam import GradCAMExplainer, apply_gradcam_overlay


class FractureInferenceEngine:
    """
    Primary CNN detector and real Grad-CAM provider for Verifact triage.
    """
    def __init__(self, checkpoint_path: Optional[str] = None):
        self.model = None
        self.target_layer = None
        self.explainer: Optional[GradCAMExplainer] = None
        self.model_version = "verifact-densenet121-v1.0"
        self.img_size = 224
        self.is_loaded = False
        self.device = "cpu"
        self.uncertainty_min = float(os.getenv("UNCERTAINTY_MIN", "0.40"))
        self.uncertainty_max = float(os.getenv("UNCERTAINTY_MAX", "0.70"))

        if checkpoint_path:
            self.load_checkpoint(checkpoint_path)
        else:
            default_ckpt = PROJECT_ROOT / "ml" / "checkpoints" / "densenet121_best.pt"
            if default_ckpt.exists():
                self.load_checkpoint(str(default_ckpt))

    def load_checkpoint(self, checkpoint_path: str):
        try:
            import torch
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
            ckpt = torch.load(checkpoint_path, map_location=self.device)

            model_name = ckpt.get("model_name", "densenet121")
            self.model, self.target_layer = build_fracture_classifier(
                model_name=model_name,
                pretrained=False,
                num_classes=1
            )
            self.model.load_state_dict(ckpt["model_state_dict"])
            self.model.to(self.device)
            self.model.eval()

            self.explainer = GradCAMExplainer(self.model, self.target_layer)
            self.model_version = f"verifact-{model_name}-epoch{ckpt.get('epoch', 1)}"
            self.is_loaded = True
            print(f"[Verifact ML] Loaded CNN checkpoint: {checkpoint_path} ({self.model_version}) on {self.device}")
        except Exception as e:
            self.is_loaded = False
            self.model_version = "verifact-densenet121-v1.0 (unloaded)"
            print(f"[Verifact ML] Warning: Could not load CNN checkpoint: {e}")

    def predict(
        self,
        image_input: Union[bytes, str, Image.Image, np.ndarray],
        decision_threshold: float = 0.50
    ) -> Dict[str, Any]:
        """
        Runs primary CNN triage prediction and real Grad-CAM generation.
        """
        # Convert input to PIL and RGB numpy
        if isinstance(image_input, bytes):
            pil_img = Image.open(io.BytesIO(image_input)).convert("RGB")
        elif isinstance(image_input, str):
            pil_img = Image.open(image_input).convert("RGB")
        elif isinstance(image_input, Image.Image):
            pil_img = image_input.convert("RGB")
        elif isinstance(image_input, np.ndarray):
            if image_input.ndim == 2:
                pil_img = Image.fromarray(cv2.cvtColor(image_input, cv2.COLOR_GRAY2RGB))
            else:
                pil_img = Image.fromarray(image_input)
        else:
            raise ValueError("Unsupported image input type.")

        rgb_np = np.array(pil_img)
        orig_h, orig_w = rgb_np.shape[:2]

        if not self.is_loaded or self.model is None or self.explainer is None:
            # Clean fallback when weights are not yet loaded
            return {
                "is_ai_analysis": False,
                "analysis_mode": "cnn_unloaded",
                "model_version": self.model_version,
                "fracture_probability": None,
                "fracture_detected": None,
                "uncertain": False,
                "gradcam_heatmap_bytes": None,
                "gradcam_array": None,
                "notice": "CNN checkpoint not loaded. Awaiting fine-tuned weights."
            }

        import torch
        from ml.dataset import get_transforms

        transform = get_transforms(img_size=self.img_size, is_train=False)
        tensor = transform(pil_img).unsqueeze(0).to(self.device)
        tensor.requires_grad = True

        # Forward pass
        logits = self.model(tensor)
        prob = float(torch.sigmoid(logits).item())
        detected = prob >= decision_threshold
        uncertain = self.uncertainty_min <= prob <= self.uncertainty_max

        # Real Grad-CAM
        heatmap_2d = self.explainer.generate_heatmap(tensor)
        blended_rgb, colored_heatmap = apply_gradcam_overlay(rgb_np, heatmap_2d, alpha=0.40)

        # Encode blended image to JPEG bytes
        is_success, buffer = cv2.imencode(".jpg", cv2.cvtColor(blended_rgb, cv2.COLOR_RGB2BGR))
        gradcam_bytes = buffer.tobytes() if is_success else None

        return {
            "is_ai_analysis": True,
            "analysis_mode": "cnn_triage",
            "model_version": self.model_version,
            "fracture_probability": round(prob, 4),
            "confidence": round(prob, 4),
            "fracture_detected": detected,
            "uncertain": uncertain,
            "gradcam_heatmap_bytes": gradcam_bytes,
            "gradcam_array": heatmap_2d,
            "notice": "Real Grad-CAM generated from convolutional feature layer."
        }


# Global singleton instance
_inference_engine: Optional[FractureInferenceEngine] = None


def get_inference_engine() -> FractureInferenceEngine:
    global _inference_engine
    if _inference_engine is None:
        _inference_engine = FractureInferenceEngine()
    return _inference_engine
