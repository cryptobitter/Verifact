"""
Model-agnostic Real Grad-CAM (Gradient-weighted Class Activation Mapping) implementation.
Hooks into the final convolutional layer of any PyTorch CNN backbone to compute
exact gradient-weighted feature activation heatmaps.
"""

from typing import Optional, Tuple
import numpy as np
import cv2


class GradCAMExplainer:
    """
    Computes real Grad-CAM heatmaps for any PyTorch vision model.
    """
    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.activations: Optional[np.ndarray] = None
        self.gradients: Optional[np.ndarray] = None
        self._handles = []
        self._register_hooks()

    def _register_hooks(self):
        def forward_hook(module, input, output):
            self.activations = output.detach()

        def backward_hook(module, grad_in, grad_out):
            self.gradients = grad_out[0].detach()

        h_f = self.target_layer.register_forward_hook(forward_hook)
        h_b = self.target_layer.register_full_backward_hook(backward_hook)
        self._handles.extend([h_f, h_b])

    def generate_heatmap(
        self,
        input_tensor,
        target_class_idx: Optional[int] = None
    ) -> np.ndarray:
        """
        Runs forward and backward passes to compute the normalized 2D Grad-CAM heatmap [0.0, 1.0].
        """
        import torch

        self.model.eval()
        self.model.zero_grad()

        output = self.model(input_tensor)

        if target_class_idx is None:
            # Single-output binary classifier or top-1 class
            if output.shape[-1] == 1:
                score = output[0, 0]
            else:
                target_class_idx = int(torch.argmax(output, dim=-1).item())
                score = output[0, target_class_idx]
        else:
            score = output[0, target_class_idx]

        score.backward(retain_graph=True)

        if self.gradients is None or self.activations is None:
            raise RuntimeError("Grad-CAM hooks failed to capture gradients or activations.")

        # Channel-wise pooling of gradients: [C]
        weights = torch.mean(self.gradients, dim=(2, 3), keepdim=True)

        # Weighted combination of forward activation maps: [1, H, W]
        cam = torch.sum(weights * self.activations, dim=1, keepdim=True)
        cam = torch.clamp(cam, min=0.0)  # ReLU

        cam_np = cam.squeeze().cpu().numpy()
        cam_max = np.max(cam_np)
        if cam_max > 0:
            cam_np = cam_np / cam_max
        else:
            cam_np = np.zeros_like(cam_np)

        return cam_np

    def overlay_on_image(
        self,
        original_image_rgb: np.ndarray,
        heatmap_2d: np.ndarray,
        alpha: float = 0.40,
        colormap: int = cv2.COLORMAP_JET
    ) -> np.ndarray:
        """
        Resizes the 2D heatmap to original image resolution, applies colormap,
        and blends with the original image at the specified alpha.
        """
        h, w = original_image_rgb.shape[:2]
        resized_cam = cv2.resize(heatmap_2d, (w, h), interpolation=cv2.INTER_LINEAR)
        cam_uint8 = np.uint8(255 * resized_cam)
        heatmap_colored = cv2.applyColorMap(cam_uint8, colormap)
        heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)

        blended = cv2.addWeighted(original_image_rgb, 1.0 - alpha, heatmap_colored, alpha, 0)
        return blended

    def remove_hooks(self):
        """Clean up hooks when explainer is discarded."""
        for h in self._handles:
            h.remove()
        self._handles.clear()


def apply_gradcam_overlay(
    original_rgb: np.ndarray,
    heatmap_2d: np.ndarray,
    alpha: float = 0.40
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Utility function to resize and blend a 2D heatmap [0, 1] onto an RGB radiograph.
    Returns (blended_rgb, colored_heatmap_rgb).
    """
    h, w = original_rgb.shape[:2]
    resized = cv2.resize(heatmap_2d, (w, h), interpolation=cv2.INTER_LINEAR)
    cam_uint8 = np.uint8(255 * np.clip(resized, 0.0, 1.0))
    heatmap_colored = cv2.applyColorMap(cam_uint8, cv2.COLORMAP_JET)
    heatmap_colored = cv2.cvtColor(heatmap_colored, cv2.COLOR_BGR2RGB)
    blended = cv2.addWeighted(original_rgb, 1.0 - alpha, heatmap_colored, alpha, 0)
    return blended, heatmap_colored
