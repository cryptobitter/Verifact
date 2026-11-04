from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ModelOutput(BaseModel):
    fracture_detected: bool
    confidence: Optional[float] = None
    bone: Optional[str] = None
    location: Optional[str] = None
    fracture_type: Optional[str] = None
    displacement: Optional[str] = None
    severity: Optional[str] = None
    report_text: Optional[str] = None
    heatmap_bytes: Optional[bytes] = None
    heatmap_data_url: Optional[str] = None


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
