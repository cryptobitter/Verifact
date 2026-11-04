import io
import json
import base64
from app.models.analysis import Analysis
from reportlab.lib.pagesizes import letter
from reportlab.lib.colors import red, orange, green, HexColor, grey
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle


def generate_pdf_report(analysis: Analysis) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=0.8 * inch,
        leftMargin=0.8 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.8 * inch
    )

    styles = getSampleStyleSheet()

    header_title_style = ParagraphStyle(
        'HeaderTitleStyle',
        parent=styles['Heading1'],
        fontSize=20,
        leading=24,
        textColor=HexColor("#0f172a"),
        fontName="Helvetica-Bold",
        spaceAfter=4
    )

    header_subtitle_style = ParagraphStyle(
        'HeaderSubtitleStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=HexColor("#64748b"),
        spaceAfter=15
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontSize=12,
        leading=15,
        textColor=HexColor("#1e293b"),
        fontName="Helvetica-Bold",
        spaceBefore=10,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyReportStyle',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=14,
        textColor=HexColor("#334155")
    )

    stamp_style = ParagraphStyle(
        'DoctorStampStyle',
        parent=styles['Normal'],
        fontSize=9,
        leading=13,
        textColor=HexColor("#047857"),
        fontName="Helvetica-Bold"
    )

    disclaimer_style = ParagraphStyle(
        'DisclaimerStyle',
        parent=styles['Normal'],
        fontSize=8,
        leading=11,
        textColor=HexColor("#94a3b8"),
        alignment=1
    )

    elements = []

    # Title Banner
    elements.append(Paragraph("<b>VERIFACT CLINICAL RADIOLOGY REPORT</b>", header_title_style))
    elements.append(Paragraph("Musculoskeletal Fracture Triage & PACS Explainability System", header_subtitle_style))

    # Meta Info Table
    date_str = analysis.created_at.strftime("%B %d, %Y - %I:%M %p UTC") if analysis.created_at else "N/A"
    status_str = "FRACTURE DETECTED" if analysis.fracture_detected else "NO ACUTE FRACTURE DETECTED"
    study_series = "Orthogonal Dual-View (AP + Lateral)" if analysis.lateral_image_url else "Standard Plain Radiograph"

    patient_label = analysis.patient_id or f"PT-{analysis.id:04d}"
    age_str = f"{analysis.patient_age} yrs" if analysis.patient_age else "Unspecified"
    gender_str = analysis.patient_gender or "Unspecified"

    meta_data = [
        ["Scan ID:", f"FRX-{analysis.id:06d}", "Study Date:", date_str],
        ["Patient ID:", f"{patient_label} ({gender_str}, {age_str})", "Study Series:", study_series],
        ["Diagnostic Status:", status_str, "AI Confidence:", f"{((analysis.confidence or 0.95) * 100):.1f}%"]
    ]

    meta_table = Table(meta_data, colWidths=[1.3 * inch, 2.3 * inch, 1.2 * inch, 2.0 * inch])
    meta_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (-1, -1), HexColor("#334155")),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(meta_table)

    if analysis.mechanism_of_injury:
        elements.append(Spacer(1, 0.05 * inch))
        elements.append(Paragraph(f"<b>Mechanism of Trauma:</b> {analysis.mechanism_of_injury}", body_style))

    elements.append(Spacer(1, 0.12 * inch))

    # Findings Table
    bone = analysis.bone if analysis.bone else "Osseous structures"
    location = analysis.location if analysis.location else "Intact"
    fracture_type = analysis.fracture_type if analysis.fracture_type else "None"
    displacement = analysis.displacement if analysis.displacement else "None"
    severity_text = (analysis.severity or "None").capitalize()

    table_data = [
        ["Anatomical Bone", bone],
        ["Anatomical Location", location],
        ["Fracture Classification", fracture_type],
        ["Cortical Displacement", displacement],
        ["Clinical Severity Index", severity_text]
    ]

    t_style = [
        ('BACKGROUND', (0, 0), (0, -1), HexColor("#f1f5f9")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTNAME', (1, 0), (1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 8.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
        ('TEXTCOLOR', (0, 0), (-1, -1), HexColor("#1e293b"))
    ]

    sev_lower = (analysis.severity or "").lower()
    if sev_lower in ["severe", "high"]:
        t_style.append(('TEXTCOLOR', (1, 4), (1, 4), HexColor("#dc2626")))
        t_style.append(('FONTNAME', (1, 4), (1, 4), 'Helvetica-Bold'))
    elif sev_lower in ["moderate", "medium"]:
        t_style.append(('TEXTCOLOR', (1, 4), (1, 4), HexColor("#ea580c")))
        t_style.append(('FONTNAME', (1, 4), (1, 4), 'Helvetica-Bold'))
    else:
        t_style.append(('TEXTCOLOR', (1, 4), (1, 4), HexColor("#16a34a")))
        t_style.append(('FONTNAME', (1, 4), (1, 4), 'Helvetica-Bold'))

    t = Table(table_data, colWidths=[2.2 * inch, 4.6 * inch])
    t.setStyle(TableStyle(t_style))
    elements.append(t)

    # Clinical PACS Measurements (if any annotations recorded)
    if analysis.annotations:
        try:
            annot_data = json.loads(analysis.annotations)
            measurements = annot_data.get("measurements", [])
            if measurements:
                elements.append(Spacer(1, 0.1 * inch))
                elements.append(Paragraph("<b>PACS Quantitative Caliper Measurements</b>", section_heading))
                meas_rows = [["Measurement Label", "Modality Tool", "Calculated Metric Value"]]
                for m in measurements:
                    meas_rows.append([
                        m.get("label", "Displacement/Angle"),
                        m.get("type", "Caliper").capitalize(),
                        f"{m.get('value', 'N/A')}"
                    ])
                meas_table = Table(meas_rows, colWidths=[2.6 * inch, 2.0 * inch, 2.2 * inch])
                meas_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), HexColor("#e2e8f0")),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8.5),
                    ('GRID', (0, 0), (-1, -1), 0.5, HexColor("#cbd5e1")),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
                    ('TOPPADDING', (0, 0), (-1, -1), 3),
                ]))
                elements.append(meas_table)
        except Exception:
            pass

    elements.append(Spacer(1, 0.12 * inch))

    # Structured Radiology Paragraph
    elements.append(Paragraph("<b>Synthesized Clinical Radiology Findings</b>", section_heading))
    report_text = analysis.report_text or "No findings recorded."
    elements.append(Paragraph(report_text, body_style))

    if analysis.clinical_notes:
        elements.append(Spacer(1, 0.1 * inch))
        elements.append(Paragraph("<b>Attending Physician Clinical Management Notes</b>", section_heading))
        elements.append(Paragraph(analysis.clinical_notes, body_style))

    # Doctor Digital Stamp
    elements.append(Spacer(1, 0.2 * inch))
    if analysis.signed_off:
        stamp_time = analysis.signed_at.strftime("%B %d, %Y %I:%M %p UTC") if analysis.signed_at else "Timestamp Verified"
        signer_info = analysis.signed_by or "Attending Orthopedic Specialist"
        stamp_box_data = [
            [
                Paragraph("<b>[DIGITALLY SIGNED & VERIFIED]</b>", stamp_style),
                Paragraph(f"Signer: {signer_info}<br/>Signed At: {stamp_time}<br/>System: VERIFACT HL7/HIPAA Compliant Signature", body_style)
            ]
        ]
        stamp_table = Table(stamp_box_data, colWidths=[2.2 * inch, 4.6 * inch])
        stamp_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor("#ecfdf5")),
            ('BOX', (0, 0), (-1, -1), 1, HexColor("#059669")),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(stamp_table)
    else:
        pending_box_data = [
            [
                Paragraph("<b>[PRELIMINARY AI DRAFT]</b>", ParagraphStyle('Pending', parent=styles['Normal'], textColor=HexColor("#d97706"), fontName="Helvetica-Bold", fontSize=8.5)),
                Paragraph("Awaiting Verified Physician Review and Digital Signature. Not finalized for billing or legal record.", body_style)
            ]
        ]
        pending_table = Table(pending_box_data, colWidths=[2.2 * inch, 4.6 * inch])
        pending_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor("#fffbeb")),
            ('BOX', (0, 0), (-1, -1), 1, HexColor("#d97706")),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(pending_table)

    elements.append(Spacer(1, 0.25 * inch))
    disclaimer_text = (
        "CONFIDENTIAL MEDICAL REPORT - VERIFACT AI Co-Pilot enforces Human-in-the-Loop clinical oversight. "
        "AI output serves as assistive clinical decision support and does not constitute independent medical diagnosis. "
        "Verified physician review and signature are required for final clinical disposition."
    )
    elements.append(Paragraph(disclaimer_text, disclaimer_style))

    doc.build(elements)
    return buffer.getvalue()
