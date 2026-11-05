"""
Audit log model for compliance, tracking user actions, reviews, and sign-offs.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True)
    action = Column(String(50), nullable=False)  # VIEW, CREATE, EDIT, SIGN_OFF, EXPORT_PDF, PRIORITY_TRIAGE
    details = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", lazy="selectin")
    analysis = relationship("Analysis", lazy="selectin")
