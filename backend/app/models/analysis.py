from app.database import Base
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime


class Analysis(Base):
    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    image_url = Column(Text, nullable=False)
    heatmap_url = Column(Text, nullable=True)
    bone = Column(String(100), nullable=True)
    location = Column(String(100), nullable=True)
    fracture_type = Column(String(100), nullable=True)
    displacement = Column(String(100), nullable=True)
    severity = Column(String(20), nullable=True)
    fracture_detected = Column(Boolean, nullable=True, default=True)
    confidence = Column(Float, nullable=True)
    report_text = Column(Text, nullable=True)
    clinical_notes = Column(Text, nullable=True)
    signed_off = Column(Boolean, nullable=True, default=False)
    signed_by = Column(String(255), nullable=True)
    signed_at = Column(DateTime, nullable=True)
    authenticity_flag = Column(Boolean, nullable=True, default=False)
    
    # Orthogonal Dual-View
    lateral_image_url = Column(Text, nullable=True)
    lateral_heatmap_url = Column(Text, nullable=True)

    # Clinical Case Demographics & Triage Context
    patient_id = Column(String(50), nullable=True)
    patient_age = Column(Integer, nullable=True)
    patient_gender = Column(String(20), nullable=True)
    mechanism_of_injury = Column(String(255), nullable=True)

    # Interactive PACS Caliper / Angle / Ruler Annotations (JSON string)
    annotations = Column(Text, nullable=True)

    # Clinical Dispatch Tracking
    email_sent_to = Column(String(255), nullable=True)
    email_sent_at = Column(DateTime, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="analyses", lazy="selectin")
