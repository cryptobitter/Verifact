from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class LlmStructuredOutput(BaseModel):
    fracture_detected: bool
    confidence: float = Field(ge=0.0, le=1.0)
    bone: Optional[str] = None
    location: Optional[str] = None
    fracture_type: Optional[str] = None
    displacement: Optional[str] = None
    severity: Optional[str] = None
    roi_coordinates: Optional[Dict[str, float]] = None


class ModelOutput(BaseModel):
    fracture_detected: Optional[bool] = None
    confidence: Optional[float] = None
    bone: Optional[str] = None
    location: Optional[str] = None
    fracture_type: Optional[str] = None
    displacement: Optional[str] = None
    severity: Optional[str] = None
    report_text: Optional[str] = None
    heatmap_bytes: Optional[bytes] = None
    heatmap_data_url: Optional[str] = None
    is_ai_analysis: bool = False
    analysis_mode: str = "offline_enhancement_only"
    notice: Optional[str] = None
    review_priority: str = "normal"
    review_reason: Optional[str] = None
    cnn_prediction: Optional[bool] = None
    cnn_probability: Optional[float] = None
    llm_prediction: Optional[bool] = None
    providers_agreed: Optional[bool] = None
    latency_ms: Optional[float] = None
    estimated_cost_usd: Optional[float] = None
    model_version: Optional[str] = "verifact-v1.0"



class AnalysisResponse(BaseModel):
    id: int
    fracture_detected: Optional[bool] = None
    confidence: Optional[float] = None
    bone: Optional[str] = None
    location: Optional[str] = None
    fracture_type: Optional[str] = None
    displacement: Optional[str] = None
    severity: Optional[str] = None
    report_text: Optional[str] = None
    clinical_notes: Optional[str] = None
    signed_off: Optional[bool] = None
    signed_by: Optional[str] = None
    signed_at: Optional[datetime] = None
    authenticity_flag: Optional[bool] = None
    image_url: str
    heatmap_url: Optional[str] = None
    lateral_image_url: Optional[str] = None
    lateral_heatmap_url: Optional[str] = None
    patient_id: Optional[str] = None
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    mechanism_of_injury: Optional[str] = None
    annotations: Optional[str] = None
    pixel_spacing: Optional[str] = None
    is_ai_analysis: Optional[bool] = False
    analysis_mode: Optional[str] = "offline_enhancement_only"
    notice: Optional[str] = None
    # Router & Disagreement Triage
    review_priority: Optional[str] = "normal"
    review_reason: Optional[str] = None
    cnn_prediction: Optional[bool] = None
    cnn_probability: Optional[float] = None
    llm_prediction: Optional[bool] = None
    providers_agreed: Optional[bool] = None
    latency_ms: Optional[float] = None
    estimated_cost_usd: Optional[float] = None
    model_version: Optional[str] = "verifact-v1.0"
    email_sent_to: Optional[str] = None
    email_sent_at: Optional[datetime] = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class AnalysisHistoryItem(BaseModel):
    id: int
    fracture_detected: Optional[bool] = None
    confidence: Optional[float] = None
    bone: Optional[str] = None
    severity: Optional[str] = None
    signed_off: Optional[bool] = None
    image_url: Optional[str] = None
    heatmap_url: Optional[str] = None
    is_ai_analysis: Optional[bool] = False
    analysis_mode: Optional[str] = "offline_enhancement_only"
    notice: Optional[str] = None
    review_priority: Optional[str] = "normal"
    review_reason: Optional[str] = None
    model_version: Optional[str] = "verifact-v1.0"
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class AnalysisUpdateRequest(BaseModel):
    bone: Optional[str] = None
    location: Optional[str] = None
    fracture_type: Optional[str] = None
    displacement: Optional[str] = None
    severity: Optional[str] = None
    report_text: Optional[str] = None
    clinical_notes: Optional[str] = None
    signed_off: Optional[bool] = None
    annotations: Optional[str] = None
    patient_id: Optional[str] = None
    patient_age: Optional[int] = None
    patient_gender: Optional[str] = None
    mechanism_of_injury: Optional[str] = None


class EmailDispatchRequest(BaseModel):
    recipient_email: str
    recipient_name: Optional[str] = None
    notes: Optional[str] = None


class JobStatusResponse(BaseModel):
    job_id: str
    status: str  # "queued", "processing", "completed", "failed"
    progress: int = 0
    result: Optional[AnalysisResponse] = None
    error: Optional[str] = None
    created_at: datetime
