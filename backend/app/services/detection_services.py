from typing import Optional, Dict, Any
from app.schemas.analysis_schema import ModelOutput
from app.services.ml_pipeline import run_dual_engine_pipeline


async def detect_fracture(image_bytes: bytes, metadata: Optional[Dict[str, Any]] = None) -> ModelOutput:
    """Invokes the dual-engine vision and Grad-CAM ML pipeline with optional DICOM metadata."""
    return await run_dual_engine_pipeline(image_bytes, metadata=metadata)
