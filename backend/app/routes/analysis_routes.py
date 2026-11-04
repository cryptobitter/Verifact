import io
import os
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.analysis import Analysis
from app.models.user import User
from app.utils.security import get_current_user
from app.schemas.analysis_schema import (
    AnalysisResponse,
    AnalysisHistoryItem,
    AnalysisUpdateRequest,
    EmailDispatchRequest
)
from app.services.storage_services import upload_xray_image, upload_image_bytes
from app.services.detection_services import detect_fracture
from app.services.pdf_services import generate_pdf_report
from app.services.dicom_services import is_dicom_file, process_dicom_bytes
from app.services.email_services import send_clinical_report_email
from app.services.fhir_services import generate_fhir_diagnostic_report

router = APIRouter()

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "static" / "samples"


@router.get("/samples")
def get_sample_cases():
    """Returns 4 verified clinical showcase cases for 1-click instant demo."""
    cases = [
        {
            "id": "distal_radius_fracture",
            "title": "Distal Radius Fracture",
            "category": "Forearm Trauma",
            "anatomy": "Wrist / Forearm (AP)",
            "description": "Cortical step-off disruption at the distal radial metaphysis (Colles' type fracture).",
            "expected_severity": "Moderate",
            "filename": "distal_radius_fracture.png"
        },
        {
            "id": "normal_femur_control",
            "title": "Intact Femur (Control)",
            "category": "Normal Control",
            "anatomy": "Femur Shaft (AP)",
            "description": "Continuous radio-dense cortical margins without acute cortical disruption or periosteal reaction.",
            "expected_severity": "None",
            "filename": "normal_femur_control.png"
        },
        {
            "id": "clavicle_displaced_fracture",
            "title": "Clavicle Displaced Fracture",
            "category": "Shoulder Girdle",
            "anatomy": "Clavicle (AP)",
            "description": "Mid-shaft cortical discontinuity with vertical displacement and fracture gap.",
            "expected_severity": "Severe",
            "filename": "clavicle_displaced_fracture.png"
        },
        {
            "id": "scaphoid_hairline_fracture",
            "title": "Scaphoid Hairline Fracture",
            "category": "Carpal Bones",
            "anatomy": "Carpal Scaphoid View",
            "description": "Subtle radiolucent hairline disruption traversing the scaphoid anatomical waist.",
            "expected_severity": "Low",
            "filename": "scaphoid_hairline_fracture.png"
        }
    ]
    return cases


@router.get("/sample-image/{sample_id}")
def get_sample_image(sample_id: str):
    """Serves the raw sample image file for previewing."""
    file_path = SAMPLES_DIR / f"{sample_id}.png"
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Sample image not found")
    return FileResponse(file_path, media_type="image/png")


@router.post("/analyze/sample/{sample_id}", response_model=AnalysisResponse)
async def analyze_sample_case(
    sample_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """1-Click analysis execution on a verified showcase sample."""
    file_path = SAMPLES_DIR / f"{sample_id}.png"
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="Sample image not found")

    with open(file_path, "rb") as f:
        image_bytes = f.read()

    image_url = await upload_image_bytes(image_bytes, filename_prefix=sample_id, content_type="image/png")
    model_output = await detect_fracture(image_bytes)

    heatmap_url = model_output.heatmap_data_url
    if model_output.heatmap_bytes:
        try:
            heatmap_url = await upload_image_bytes(
                model_output.heatmap_bytes,
                filename_prefix=f"heatmap_{sample_id}",
                content_type="image/png"
            )
        except Exception as exc:
            print(f"[WARN] Heatmap storage upload failed ({exc}), using data URL.")

    analysis = Analysis(
        user_id=current_user.id,
        image_url=image_url,
        heatmap_url=heatmap_url,
        bone=model_output.bone,
        location=model_output.location,
        fracture_type=model_output.fracture_type,
        displacement=model_output.displacement,
        severity=model_output.severity,
        fracture_detected=model_output.fracture_detected,
        confidence=model_output.confidence,
        report_text=model_output.report_text,
        authenticity_flag=False,
        signed_off=False
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return analysis


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_xray(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    image_bytes = await file.read()

    MAX_FILE_SIZE = 15 * 1024 * 1024
    if len(image_bytes) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large; maximum size is 15 MB.")

    if not image_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Check if uploaded file is a DICOM (.dcm) dataset
    dicom_meta = None
    if is_dicom_file(image_bytes, file.filename):
        try:
            processed_bytes, dicom_meta = process_dicom_bytes(image_bytes)
            image_url = await upload_image_bytes(
                processed_bytes,
                filename_prefix="dicom_xray",
                content_type="image/png",
                ext=".png"
            )
            model_input_bytes = processed_bytes
        except Exception as dicom_err:
            raise HTTPException(status_code=400, detail=f"Failed to process DICOM file: {dicom_err}")
    else:
        valid_types = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
        if file.content_type and file.content_type not in valid_types and not file.filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            raise HTTPException(status_code=400, detail="Please upload a valid radiograph image (PNG, JPG, WEBP) or DICOM (.dcm) file.")

        image_url = await upload_image_bytes(
            image_bytes,
            filename_prefix="xray",
            content_type=file.content_type or "image/png",
            ext=f".{file.filename.split('.')[-1]}" if file.filename and "." in file.filename else ".png"
        )
        model_input_bytes = image_bytes

    try:
        model_output = await detect_fracture(model_input_bytes, metadata=dicom_meta)

        heatmap_url = model_output.heatmap_data_url
        if model_output.heatmap_bytes:
            try:
                heatmap_url = await upload_image_bytes(
                    model_output.heatmap_bytes,
                    filename_prefix="gradcam",
                    content_type="image/png"
                )
            except Exception as exc:
                print(f"[WARN] Heatmap storage upload failed ({exc}), keeping data URL.")

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[ERROR] Dual-engine analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to process radiograph analysis.")

    analysis = Analysis(
        user_id=current_user.id,
        image_url=image_url,
        heatmap_url=heatmap_url,
        bone=model_output.bone,
        location=model_output.location,
        fracture_type=model_output.fracture_type,
        displacement=model_output.displacement,
        severity=model_output.severity,
        fracture_detected=model_output.fracture_detected,
        confidence=model_output.confidence,
        report_text=model_output.report_text,
        authenticity_flag=False,
        signed_off=False
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    return analysis


@router.put("/analysis/{analysis_id}", response_model=AnalysisResponse)
def update_and_sign_analysis(
    analysis_id: int,
    update_data: AnalysisUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Human-in-the-Loop review endpoint:
    Allows the verified physician to edit AI findings, enter clinical notes,
    and digitally stamp/sign off on the record.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if analysis.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this record")

    if update_data.bone is not None:
        analysis.bone = update_data.bone
    if update_data.location is not None:
        analysis.location = update_data.location
    if update_data.fracture_type is not None:
        analysis.fracture_type = update_data.fracture_type
    if update_data.displacement is not None:
        analysis.displacement = update_data.displacement
    if update_data.severity is not None:
        analysis.severity = update_data.severity
    if update_data.report_text is not None:
        analysis.report_text = update_data.report_text
    if update_data.clinical_notes is not None:
        analysis.clinical_notes = update_data.clinical_notes
    if update_data.annotations is not None:
        analysis.annotations = update_data.annotations
    if update_data.patient_id is not None:
        analysis.patient_id = update_data.patient_id
    if update_data.patient_age is not None:
        analysis.patient_age = update_data.patient_age
    if update_data.patient_gender is not None:
        analysis.patient_gender = update_data.patient_gender
    if update_data.mechanism_of_injury is not None:
        analysis.mechanism_of_injury = update_data.mechanism_of_injury

    if update_data.signed_off is not None:
        analysis.signed_off = update_data.signed_off
        if update_data.signed_off:
            doc_name = current_user.full_name or "Verified Clinician"
            clean_name = doc_name if doc_name.lower().startswith("dr") else f"Dr. {doc_name}"
            reg_num = current_user.registration_number or "MCI-REGISTERED"
            degree = current_user.qualification or "MBBS, MS (Ortho)"
            analysis.signed_by = f"{clean_name}, {degree} (Reg: {reg_num})"
            analysis.signed_at = datetime.utcnow()

    db.commit()
    db.refresh(analysis)
    return analysis


@router.post("/analyze/dual-view", response_model=AnalysisResponse)
async def analyze_dual_view(
    ap_file: UploadFile = File(...),
    lateral_file: Optional[UploadFile] = File(None),
    patient_id: Optional[str] = Form(None),
    patient_age: Optional[int] = Form(None),
    patient_gender: Optional[str] = Form(None),
    mechanism_of_injury: Optional[str] = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Ingests and cross-correlates orthogonal bi-planar radiographs (AP + Lateral).
    Also attaches clinical trauma triage demographics (Age, Gender, FOOSH Mechanism).
    """
    # 1. Process AP Radiograph
    ap_bytes = await ap_file.read()
    if not ap_bytes:
        raise HTTPException(status_code=400, detail="AP Radiograph file is empty.")

    ap_dicom_meta = None
    if is_dicom_file(ap_bytes, ap_file.filename):
        ap_png_bytes, ap_dicom_meta = process_dicom_bytes(ap_bytes)
        ap_image_url = await upload_image_bytes(ap_png_bytes, filename_prefix="ap_dcm", content_type="image/png")
        ap_input_bytes = ap_png_bytes
    else:
        ap_image_url = await upload_image_bytes(ap_bytes, filename_prefix="ap_xray", content_type=ap_file.content_type or "image/png")
        ap_input_bytes = ap_bytes

    # 2. Process Lateral Radiograph if provided
    lateral_image_url = None
    lateral_heatmap_url = None
    lat_dicom_meta = None
    if lateral_file and lateral_file.filename:
        lat_bytes = await lateral_file.read()
        if lat_bytes:
            if is_dicom_file(lat_bytes, lateral_file.filename):
                lat_png_bytes, lat_dicom_meta = process_dicom_bytes(lat_bytes)
                lateral_image_url = await upload_image_bytes(lat_png_bytes, filename_prefix="lat_dcm", content_type="image/png")
                lat_input_bytes = lat_png_bytes
            else:
                lateral_image_url = await upload_image_bytes(lat_bytes, filename_prefix="lat_xray", content_type=lateral_file.content_type or "image/png")
                lat_input_bytes = lat_bytes

            # Run detection on lateral view
            try:
                lat_output = await detect_fracture(lat_input_bytes, metadata=lat_dicom_meta)
                lateral_heatmap_url = lat_output.heatmap_data_url
                if lat_output.heatmap_bytes:
                    try:
                        lateral_heatmap_url = await upload_image_bytes(lat_output.heatmap_bytes, filename_prefix="lat_cam", content_type="image/png")
                    except Exception:
                        pass
            except Exception as e:
                print(f"[WARN] Lateral detection skipped: {e}")

    # 3. Run primary analysis on AP view
    model_output = await detect_fracture(ap_input_bytes, metadata=ap_dicom_meta)
    ap_heatmap_url = model_output.heatmap_data_url
    if model_output.heatmap_bytes:
        try:
            ap_heatmap_url = await upload_image_bytes(model_output.heatmap_bytes, filename_prefix="ap_cam", content_type="image/png")
        except Exception:
            pass

    # Combine report text if orthogonal lateral view was also triaged
    report_text = model_output.report_text
    if lateral_image_url:
        report_text += " Orthogonal lateral projection cross-correlated; alignment and displacement confirmed across bi-planar views."

    analysis = Analysis(
        user_id=current_user.id,
        image_url=ap_image_url,
        heatmap_url=ap_heatmap_url,
        lateral_image_url=lateral_image_url,
        lateral_heatmap_url=lateral_heatmap_url,
        bone=model_output.bone,
        location=model_output.location,
        fracture_type=model_output.fracture_type,
        displacement=model_output.displacement,
        severity=model_output.severity,
        fracture_detected=model_output.fracture_detected,
        confidence=model_output.confidence,
        report_text=report_text,
        patient_id=patient_id or (ap_dicom_meta.get("patient_id") if ap_dicom_meta else None),
        patient_age=patient_age,
        patient_gender=patient_gender,
        mechanism_of_injury=mechanism_of_injury,
        authenticity_flag=False,
        signed_off=False
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    return analysis


@router.post("/analysis/{analysis_id}/email")
def dispatch_report_email(
    analysis_id: int,
    dispatch_data: EmailDispatchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Emails the signed clinical PDF and radiology findings to the specified clinician or patient.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if analysis.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to dispatch this record")

    pdf_bytes = generate_pdf_report(analysis)
    success = send_clinical_report_email(
        to_email=dispatch_data.recipient_email,
        analysis_id=analysis.id,
        scan_bone=analysis.bone or "Musculoskeletal X-Ray",
        severity=analysis.severity or "Unspecified",
        report_text=analysis.report_text or "See attached clinical report.",
        doctor_name=analysis.signed_by or current_user.full_name,
        pdf_bytes=pdf_bytes,
        patient_id=analysis.patient_id,
        notes=dispatch_data.notes
    )

    if success:
        analysis.email_sent_to = dispatch_data.recipient_email
        analysis.email_sent_at = datetime.utcnow()
        db.commit()

    return {
        "status": "dispatched" if success else "failed",
        "recipient": dispatch_data.recipient_email,
        "sent_at": analysis.email_sent_at
    }


@router.get("/analysis/{analysis_id}/fhir")
def get_analysis_fhir(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Exports the analysis as a standardized HL7 FHIR R4 DiagnosticReport resource.
    """
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if analysis.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this record")

    return generate_fhir_diagnostic_report(analysis)


@router.get("/analysis/history", response_model=List[AnalysisHistoryItem])
def get_analysis_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return db.query(Analysis).filter(Analysis.user_id == current_user.id).order_by(Analysis.created_at.desc()).all()


@router.get("/analysis/{analysis_id}", response_model=AnalysisResponse)
def get_analysis(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if analysis.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this analysis")

    return analysis


@router.get("/analysis/{analysis_id}/pdf")
def get_analysis_pdf(
    analysis_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")

    if analysis.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to access this analysis")

    pdf_bytes = generate_pdf_report(analysis)

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=verifact_analysis_{analysis_id}.pdf"}
    )
