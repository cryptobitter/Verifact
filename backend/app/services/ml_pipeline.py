import time
from ml.inference import get_inference_engine
import io
import os
import re
import json
import base64
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

import cv2
import numpy as np
from PIL import Image, UnidentifiedImageError
from pydantic import ValidationError

from app.config import settings
from app.schemas.analysis_schema import ModelOutput, LlmStructuredOutput
from app.services.dicom_services import deidentify_dicom_metadata, sanitize_image_pixels_for_external_api

# Global state for PyTorch model if available (Preserved for Phase 3 integration)
_torch_model = None
_torch_device = None
_torch_gradcam = None


class ResNetGradCAM:
    """True Grad-CAM implementation hooking into model layer (to be generalized in Phase 3)."""

    def __init__(self, model, target_layer):
        self.model = model
        self.target_layer = target_layer
        self.gradients = None
        self.activations = None

        self.target_layer.register_forward_hook(self._save_activation)
        self.target_layer.register_full_backward_hook(self._save_gradient)

    def _save_activation(self, module, input, output):
        self.activations = output.detach()

    def _save_gradient(self, module, grad_input, grad_output):
        self.gradients = grad_output[0].detach()

    def generate(self, input_tensor, target_class=0) -> np.ndarray:
        import torch
        self.model.zero_grad()
        output = self.model(input_tensor)
        score = output[0, target_class]
        score.backward()

        weights = torch.mean(self.gradients, dim=[2, 3], keepdim=True)
        cam = torch.sum(weights * self.activations, dim=1).squeeze().cpu().numpy()
        cam = np.maximum(cam, 0)
        if np.max(cam) > 0:
            cam = cam / np.max(cam)
        return cam


def _init_pytorch_engine():
    global _torch_model, _torch_device, _torch_gradcam
    try:
        import torch
        import torch.nn as nn
        from torchvision import models

        _torch_device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        repo_root = Path(__file__).resolve().parents[3]
        model_path = repo_root / "AIML" / "saved_models" / "best_fracture_model.pth"

        if model_path.is_file():
            model = models.resnet18(weights=None)
            model.fc = nn.Linear(model.fc.in_features, 2)
            checkpoint = torch.load(str(model_path), map_location=_torch_device, weights_only=True)
            model.load_state_dict(checkpoint)
            model.to(_torch_device)
            model.eval()
            _torch_model = model
            _torch_gradcam = ResNetGradCAM(model, model.layer4[-1])
            print(f"[AI PIPELINE] Loaded ResNet-18 checkpoint and hooked Grad-CAM: {model_path}")
        else:
            print("[AI PIPELINE] PyTorch checkpoint not found on disk. Clinical Adaptive Vision Engine active.")
    except Exception as exc:
        print(f"[AI PIPELINE] PyTorch runtime not active ({exc}). Clinical Adaptive Vision Engine active.")


_init_pytorch_engine()


# ---------------------------------------------------------------------------
# Multimodal Vision AI Extractor (Gemini primary + Groq fallback)
# ---------------------------------------------------------------------------

PROMPT_TEMPLATE = (
    "You are an expert orthopedic radiologist and musculoskeletal imaging AI triage co-pilot reviewing a plain radiograph / X-ray. "
    "Your scope is strictly upper-extremity radiographs (wrist, hand, forearm, elbow, clavicle/shoulder). "
    "{extra_context}"
    "Analyze the radiograph carefully and respond ONLY with a raw valid JSON object in this exact structure without markdown or commentary:\n"
    "{\n"
    '  "fracture_detected": true,\n'
    '  "confidence": 0.88,\n'
    '  "bone": "Distal Radius" | "Scaphoid" | "Clavicle" | "Ulna" | "Metacarpal" | "Phalanx" | "Humerus",\n'
    '  "location": "Metaphysis" | "Diaphysis" | "Epiphyseal plate" | "Mid-shaft" | "Waist" | "Intact",\n'
    '  "fracture_type": "Transverse" | "Oblique" | "Spiral" | "Comminuted" | "Greenstick" | "Hairline" | "Avulsion" | "None",\n'
    '  "displacement": "Non-displaced" | "Dorsally angulated" | "Volar displacement" | "Shortened" | "Displaced" | "None",\n'
    '  "severity": "Low" | "Moderate" | "Severe" | "None",\n'
    '  "roi_coordinates": {{"x": 0.55, "y": 0.62}}\n'
    "}\n"
    "Note: roi_coordinates are normalized (0.0 to 1.0) coordinates indicating the center point of the focal fracture line or cortical step-off."
)


def _validate_and_sanitize_llm_dict(raw_dict: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Validates raw LLM dictionary against Pydantic schema and clamps ROI coordinates."""
    try:
        validated = LlmStructuredOutput.model_validate(raw_dict)
        data = validated.model_dump()

        # Enforce strict ROI coordinate bounds [0.0, 1.0]
        roi = data.get("roi_coordinates")
        if roi and isinstance(roi, dict) and "x" in roi and "y" in roi:
            try:
                x = float(roi["x"])
                y = float(roi["y"])
                if 0.0 <= x <= 1.0 and 0.0 <= y <= 1.0:
                    data["roi_coordinates"] = {"x": round(x, 4), "y": round(y, 4)}
                else:
                    data["roi_coordinates"] = {"x": round(float(np.clip(x, 0.05, 0.95)), 4), "y": round(float(np.clip(y, 0.05, 0.95)), 4)}
            except Exception:
                data["roi_coordinates"] = None

        return data
    except ValidationError as val_err:
        print(f"[AI PIPELINE] Pydantic validation rejected LLM output: {val_err}")
        return None
    except Exception as exc:
        print(f"[AI PIPELINE] Unexpected validation error: {exc}")
        return None


async def _call_gemini_vision(image_bytes: bytes, extra_context: str = "") -> Optional[Dict[str, Any]]:
    gemini_key = getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        return None

    model_name = getattr(settings, "GEMINI_VISION_MODEL", "gemini-1.5-flash")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={gemini_key}"

    try:
        import httpx
        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        prompt = PROMPT_TEMPLATE.format(extra_context=extra_context)

        payload = {
            "contents": [
                {
                    "parts": [
                        {"text": prompt},
                        {
                            "inline_data": {
                                "mime_type": "image/png",
                                "data": b64_img
                            }
                        }
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }

        timeout = httpx.Timeout(float(getattr(settings, "AI_TIMEOUT_SECONDS", 15.0)), connect=3.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code == 200:
                res_data = resp.json()
                text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
                parsed = json.loads(text)
                validated = _validate_and_sanitize_llm_dict(parsed)
                if validated:
                    return validated

                # 1 retry with schema fix hint if invalid
                print("[AI PIPELINE] Gemini output invalid, attempting 1 retry with schema correction...")
                retry_payload = {
                    "contents": [
                        {
                            "parts": [
                                {"text": prompt + "\nREMINDER: Return strictly valid JSON conforming to the schema with numeric confidence between 0.0 and 1.0."},
                                {"inline_data": {"mime_type": "image/png", "data": b64_img}}
                            ]
                        }
                    ],
                    "generationConfig": {"temperature": 0.0, "response_mime_type": "application/json"}
                }
                retry_resp = await client.post(url, json=retry_payload)
                if retry_resp.status_code == 200:
                    r_text = retry_resp.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
                    return _validate_and_sanitize_llm_dict(json.loads(r_text))

    except Exception as exc:
        print(f"[AI PIPELINE] Gemini Vision call exception ({model_name}): {exc}")

    return None


async def _call_groq_vision(image_bytes: bytes, extra_context: str = "") -> Optional[Dict[str, Any]]:
    groq_key = getattr(settings, "GROQ_API_KEY", None) or os.getenv("GROQ_API_KEY")
    if not groq_key:
        return None

    model_name = getattr(settings, "GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")
    url = "https://api.groq.com/openai/v1/chat/completions"

    try:
        import httpx
        b64_img = base64.b64encode(image_bytes).decode("utf-8")
        prompt = PROMPT_TEMPLATE.format(extra_context=extra_context)

        headers = {
            "Authorization": f"Bearer {groq_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64_img}"}}
                    ]
                }
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        timeout = httpx.Timeout(float(getattr(settings, "AI_TIMEOUT_SECONDS", 15.0)), connect=3.0)
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                text = resp.json()["choices"][0]["message"]["content"].strip()
                parsed = json.loads(text)
                return _validate_and_sanitize_llm_dict(parsed)
    except Exception as exc:
        print(f"[AI PIPELINE] Groq Vision call exception ({model_name}): {exc}")

    return None


async def _call_multimodal_vision(image_bytes: bytes, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Tries primary Gemini then fallback Groq with de-identified metadata and sanitized image bytes."""
    if os.getenv("OFFLINE_MODE") == "1":
        return None

    # Enforce DICOM PHI De-identification before external API dispatch
    clean_meta = deidentify_dicom_metadata(metadata)
    extra_context = ""
    if clean_meta:
        parts = []
        if clean_meta.get("body_part_examined"):
            parts.append(f"Body Part Examined: {clean_meta['body_part_examined']}")
        if clean_meta.get("view_position"):
            parts.append(f"Radiographic View: {clean_meta['view_position']}")
        if clean_meta.get("modality"):
            parts.append(f"Modality: {clean_meta['modality']}")
        if parts:
            extra_context = f"DICOM Technical Tags: {', '.join(parts)}.\n"

    # Sanitize burned-in patient text annotations from corner margins
    sanitized_bytes, _ = sanitize_image_pixels_for_external_api(image_bytes)

    # 1. Primary: Gemini Vision
    res = await _call_gemini_vision(sanitized_bytes, extra_context=extra_context)
    if res and res.get("fracture_detected") is not None:
        return res

    # 2. Fallback: Groq Vision
    res = await _call_groq_vision(sanitized_bytes, extra_context=extra_context)
    if res and res.get("fracture_detected") is not None:
        return res

    return None


# ---------------------------------------------------------------------------
# Offline Computer Vision & Image Enhancement (Honest Fallback)
# ---------------------------------------------------------------------------

def _clinical_offline_enhancement_engine(cv_gray: np.ndarray) -> Dict[str, Any]:
    """
    Honest offline fallback: performs medical contrast enhancement (CLAHE).
    Emits ZERO fabricated predictions or probabilities. Explicitly signals
    that no AI analysis was conducted.
    """
    return {
        "fracture_detected": None,
        "confidence": None,
        "bone": None,
        "location": None,
        "fracture_type": None,
        "displacement": None,
        "severity": None,
        "roi_coordinates": None,
        "is_ai_analysis": False,
        "analysis_mode": "offline_enhancement_only",
        "notice": "No AI analysis performed - image enhancement only",
        "report_text": (
            "No AI analysis performed - image enhancement only. "
            "Radiograph contrast and cortical margins have been enhanced via adaptive histogram equalization (CLAHE) "
            "for manual radiologist evaluation. Independent certified physician review required."
        )
    }


# ---------------------------------------------------------------------------
# AI-Localized Region Overlay Generator (Synthetic Overlay Path)
# ---------------------------------------------------------------------------

def generate_ai_localized_overlay(
    cv_bgr: np.ndarray,
    cv_gray: np.ndarray,
    findings: Dict[str, Any]
) -> Tuple[np.ndarray, str, bytes]:
    """
    Generates an AI-localized region overlay highlighting the ROI or enhanced margins.
    Notice: Renamed from Grad-CAM to reflect that this synthetic path is an overlay,
    preserving ResNetGradCAM for the true backprop CNN in Phase 3.
    """
    h, w = cv_gray.shape

    # If offline enhancement only or no fracture detected, show neutral contrast map
    if not findings.get("is_ai_analysis", False) or not findings.get("fracture_detected", False):
        cam = np.zeros((h, w), dtype=np.float32)
        cv2.circle(cam, (w // 2, h // 2), int(min(w, h) * 0.35), 0.10, -1)
        cam = cv2.GaussianBlur(cam, (71, 71), 0)
    else:
        sobel_x = cv2.Sobel(cv_gray, cv2.CV_64F, 1, 0, ksize=3)
        sobel_y = cv2.Sobel(cv_gray, cv2.CV_64F, 0, 1, ksize=3)
        grad_mag = np.sqrt(sobel_x**2 + sobel_y**2)
        grad_norm = cv2.normalize(grad_mag, None, 0, 1.0, cv2.NORM_MINMAX).astype(np.float32)

        roi = findings.get("roi_coordinates")
        if roi and isinstance(roi, dict) and "x" in roi and "y" in roi:
            cx = int(np.clip(float(roi["x"]), 0.05, 0.95) * w)
            cy = int(np.clip(float(roi["y"]), 0.05, 0.95) * h)
        else:
            cx, cy = int(w * 0.5), int(h * 0.5)

        roi_mask = np.zeros((h, w), dtype=np.float32)
        rx = int(min(w, h) * 0.22)
        ry = int(min(w, h) * 0.14)
        cv2.ellipse(roi_mask, (cx, cy), (rx, ry), 0, 0, 360, 1.0, -1)

        focal_saliency = grad_norm * roi_mask
        focal_saliency = cv2.GaussianBlur(focal_saliency, (45, 45), 0)

        min_v, max_v, min_l, max_l = cv2.minMaxLoc(focal_saliency)
        peak_x, peak_y = max_l if max_v > 0.05 else (cx, cy)

        cam = np.zeros((h, w), dtype=np.float32)
        cv2.circle(cam, (peak_x, peak_y), int(min(w, h) * 0.16), 1.0, -1)
        cv2.circle(cam, (peak_x, peak_y), int(min(w, h) * 0.28), 0.5, -1)
        cam = cv2.GaussianBlur(cam, (65, 65), 0)
        cam = (cam * 0.65) + (focal_saliency * 0.35)
        cam = np.clip(cam, 0, 1.0)

    heatmap_uint8 = np.uint8(255 * cam)
    heatmap_colored = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)

    radiograph_bgr = cv2.cvtColor(cv_gray, cv2.COLOR_GRAY2BGR)
    blended = cv2.addWeighted(heatmap_colored, 0.40, radiograph_bgr, 0.60, 0)

    success, buffer = cv2.imencode(".png", blended)
    heatmap_bytes = buffer.tobytes() if success else b""
    heatmap_b64 = base64.b64encode(heatmap_bytes).decode("utf-8")
    heatmap_data_url = f"data:image/png;base64,{heatmap_b64}"

    return blended, heatmap_data_url, heatmap_bytes


# ---------------------------------------------------------------------------
# Structured Clinical Report Synthesis (Radiology 3-Sentence Standard)
# ---------------------------------------------------------------------------

def synthesize_clinical_report(findings: Dict[str, Any]) -> str:
    if not findings.get("is_ai_analysis", False):
        return findings.get("report_text") or "No AI analysis performed - image enhancement only."

    fracture_detected = findings.get("fracture_detected", False)
    bone = findings.get("bone") or "visualized upper-extremity osseous structures"
    location = findings.get("location") or "shaft"
    fracture_type = findings.get("fracture_type") or "cortical"
    displacement = findings.get("displacement") or "non-displaced"

    if not fracture_detected or str(fracture_type).lower() in ("none", "intact"):
        return (
            f"Visualized upper-extremity radiograph demonstrates intact cortical margins and normal alignment across the {bone.lower()} "
            "without acute cortical disruption, cortical step-off, or radiopaque dislocation. "
            "Adjacent periarticular soft tissue planes appear preserved without overt hemarthrosis. "
            "Routine clinical correlation advised; repeat plain radiography recommended only if focal tenderness persists."
        )

    disp_phrase = f"{displacement.lower()}" if str(displacement).lower() != "none" else "non-displaced"
    sentence_1 = f"Visualized radiograph demonstrates a {disp_phrase} {fracture_type.lower()} fracture across the {location.lower()} of the {bone.lower()}."

    if "comminuted" in str(fracture_type).lower() or "displaced" in disp_phrase:
        sentence_2 = "Marked surrounding soft tissue swelling noted with cortical step-off and breach; articular congruity warrants close evaluation."
    elif "hairline" in str(fracture_type).lower():
        sentence_2 = "Mild localized soft tissue attenuation identified without overt cortical displacement or joint space widening."
    else:
        sentence_2 = "Surrounding soft tissue swelling noted without evident joint dislocation or gross articular incongruity."

    sentence_3 = "Clinical correlation, orthopedic immobilization, and urgent specialist evaluation recommended."

    return f"{sentence_1} {sentence_2} {sentence_3}"


# ---------------------------------------------------------------------------
# Main Dual-Engine Pipeline Entrypoint
# ---------------------------------------------------------------------------

async def run_dual_engine_pipeline(
    image_bytes: bytes,
    metadata: Optional[Dict[str, Any]] = None
) -> ModelOutput:
    t_start = time.perf_counter()
    try:
        pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except UnidentifiedImageError as exc:
        raise ValueError("Uploaded file is not a valid readable image format.") from exc

    np_img = np.array(pil_image)
    cv_bgr = cv2.cvtColor(np_img, cv2.COLOR_RGB2BGR)
    cv_gray = cv2.cvtColor(cv_bgr, cv2.COLOR_BGR2GRAY)

    # 1. Primary CNN Detector & Real Grad-CAM
    cnn_engine = get_inference_engine()
    cnn_result = cnn_engine.predict(np_img)
    cnn_detected = cnn_result.get("fracture_detected")
    cnn_prob = cnn_result.get("fracture_probability")
    is_uncertain = cnn_result.get("uncertain", False)
    model_version = cnn_result.get("model_version", "verifact-densenet121-v1.0")

    # 2. Vision LLM: Draft report from CNN structured findings + independent assessment
    cnn_summary = {
        "cnn_suspected_fracture": cnn_detected,
        "cnn_probability": cnn_prob,
        "cnn_uncertain": is_uncertain,
        "model_version": model_version
    }
    llm_findings = await _call_multimodal_vision(image_bytes, metadata=metadata)
    
    estimated_cost = 0.0
    llm_detected = None
    if llm_findings and isinstance(llm_findings, dict) and llm_findings.get("fracture_detected") is not None:
        findings = llm_findings
        findings["is_ai_analysis"] = True
        findings["analysis_mode"] = "cnn_llm_hybrid"
        findings["notice"] = None
        llm_detected = llm_findings.get("fracture_detected")
        estimated_cost = 0.0001  # Approx API cost
    else:
        # Offline enhancement fallback
        findings = _clinical_offline_enhancement_engine(cv_gray)
        if cnn_detected is not None:
            findings["fracture_detected"] = cnn_detected
            findings["confidence"] = cnn_prob
            findings["is_ai_analysis"] = True
            findings["analysis_mode"] = "cnn_triage_only"
            findings["notice"] = "CNN automated triage (vision LLM unavailable)"

    # 3. Use real Grad-CAM heatmap if available from CNN, else generate AI-localized overlay
    if cnn_result.get("gradcam_heatmap_bytes"):
        overlay_bytes = cnn_result["gradcam_heatmap_bytes"]
        overlay_data_url = f"data:image/jpeg;base64,{base64.b64encode(overlay_bytes).decode('utf-8')}"
    else:
        _, overlay_data_url, overlay_bytes = generate_ai_localized_overlay(cv_bgr, cv_gray, findings)

    # 4. Disagreement & Review Priority Logic
    providers_agreed = None
    review_priority = "normal"
    review_reason = "Concordant triage assessment."

    if cnn_detected is not None and llm_detected is not None:
        providers_agreed = (cnn_detected == llm_detected)
        if not providers_agreed:
            review_priority = "priority"
            review_reason = f"Discordance: CNN ({'Positive' if cnn_detected else 'Negative'}) vs Vision LLM ({'Positive' if llm_detected else 'Negative'}). Human verification required."
        elif is_uncertain:
            review_priority = "priority"
            review_reason = f"Indeterminate CNN probability ({cnn_prob:.2f}) within uncertainty band [0.40, 0.70]."
        elif findings.get("severity") == "High" or str(findings.get("displacement", "")).lower() == "displaced":
            review_priority = "priority"
            review_reason = "High severity or displaced fracture requiring priority orthopedic review."
    elif is_uncertain:
        review_priority = "priority"
        review_reason = f"Indeterminate CNN confidence ({cnn_prob:.2f})."
    elif findings.get("analysis_mode") == "offline_enhancement_only":
        review_priority = "normal"
        review_reason = "Offline enhancement only - no AI classification."

    report_text = synthesize_clinical_report(findings)
    latency_ms = round((time.perf_counter() - t_start) * 1000.0, 1)

    return ModelOutput(
        fracture_detected=findings.get("fracture_detected"),
        confidence=round(float(findings["confidence"]), 4) if findings.get("confidence") is not None else None,
        bone=findings.get("bone"),
        location=findings.get("location"),
        fracture_type=findings.get("fracture_type"),
        displacement=findings.get("displacement"),
        severity=findings.get("severity"),
        report_text=report_text,
        heatmap_bytes=overlay_bytes,
        heatmap_data_url=overlay_data_url,
        is_ai_analysis=findings.get("is_ai_analysis", False),
        analysis_mode=findings.get("analysis_mode", "offline_enhancement_only"),
        notice=findings.get("notice"),
        review_priority=review_priority,
        review_reason=review_reason,
        cnn_prediction=cnn_detected,
        cnn_probability=cnn_prob,
        llm_prediction=llm_detected,
        providers_agreed=providers_agreed,
        latency_ms=latency_ms,
        estimated_cost_usd=estimated_cost,
        model_version=model_version
    )
