from typing import Dict, Any
from app.models.analysis import Analysis


def generate_fhir_diagnostic_report(analysis: Analysis) -> Dict[str, Any]:
    """
    Generates a HL7 FHIR (Fast Healthcare Interoperability Resources) R4
    DiagnosticReport resource conforming to US Core / international imaging profile.
    """
    report_id = f"FRX-RPT-{analysis.id:06d}"
    status = "final" if analysis.signed_off else "preliminary"
    patient_id = analysis.patient_id or f"PT-{analysis.id:04d}"

    # Build observations list
    observations = []
    
    # Observation 1: Fracture detection finding
    observations.append({
        "resourceType": "Observation",
        "id": f"OBS-FX-{analysis.id}",
        "status": status,
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "72170-4",
                "display": "Bone fracture findings"
            }]
        },
        "valueBoolean": bool(analysis.fracture_detected),
        "interpretation": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation",
                "code": "A" if analysis.fracture_detected else "N",
                "display": "Abnormal" if analysis.fracture_detected else "Normal"
            }]
        }]
    })

    # Observation 2: Anatomical localization & severity
    if analysis.bone:
        observations.append({
            "resourceType": "Observation",
            "id": f"OBS-ANAT-{analysis.id}",
            "status": status,
            "code": {
                "coding": [{
                    "system": "http://snomed.info/sct",
                    "code": "125605004",
                    "display": f"{analysis.bone} structure"
                }]
            },
            "bodySite": {
                "text": f"{analysis.bone} ({analysis.location or 'unspecified location'})"
            },
            "component": [
                {
                    "code": {"text": "Fracture Classification"},
                    "valueString": analysis.fracture_type or "None"
                },
                {
                    "code": {"text": "Cortical Displacement"},
                    "valueString": analysis.displacement or "None"
                },
                {
                    "code": {"text": "Severity Index"},
                    "valueString": (analysis.severity or "None").capitalize()
                }
            ]
        })

    # Main FHIR DiagnosticReport resource
    fhir_report = {
        "resourceType": "DiagnosticReport",
        "id": report_id,
        "meta": {
            "profile": ["http://hl7.org/fhir/us/core/StructureDefinition/us-core-diagnosticreport-note"],
            "versionId": "1.0",
            "lastUpdated": (analysis.signed_at or analysis.created_at).isoformat() if analysis.created_at else None
        },
        "status": status,
        "category": [{
            "coding": [{
                "system": "http://terminology.hl7.org/CodeSystem/v2-0074",
                "code": "RAD",
                "display": "Radiology"
            }]
        }],
        "code": {
            "coding": [{
                "system": "http://loinc.org",
                "code": "18748-4",
                "display": "Diagnostic imaging report"
            }],
            "text": "Musculoskeletal Radiograph Fracture Triage Report"
        },
        "subject": {
            "reference": f"Patient/{patient_id}",
            "display": f"Patient {patient_id} ({analysis.patient_gender or 'Unspecified'}, Age: {analysis.patient_age or 'N/A'})"
        },
        "effectiveDateTime": analysis.created_at.isoformat() if analysis.created_at else None,
        "issued": (analysis.signed_at or analysis.created_at).isoformat() if analysis.created_at else None,
        "performer": [{
            "display": analysis.signed_by or "VERIFACT Clinical Radiologist"
        }],
        "conclusion": analysis.report_text or "No acute bony abnormalities identified.",
        "contained": observations
    }

    if analysis.mechanism_of_injury:
        fhir_report["extension"] = [{
            "url": "http://hl7.org/fhir/StructureDefinition/clinical-injury-mechanism",
            "valueString": analysis.mechanism_of_injury
        }]

    return fhir_report
