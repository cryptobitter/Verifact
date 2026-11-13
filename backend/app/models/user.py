from sqlalchemy import Column, Integer, String, DateTime, Boolean, Date
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    is_verified = Column(Boolean, default=True, nullable=False)
    otp_code = Column(String, nullable=True)
    otp_expires_at = Column(DateTime(timezone=True), nullable=True)

    # Core user & doctor profile fields
    role = Column(String(50), nullable=False, default="radiologist")  # radiologist / resident / admin
    full_name = Column(String(255), nullable=True)
    institution = Column(String(255), nullable=True)
    department = Column(String(100), nullable=True)
    license_number = Column(String(100), nullable=True)

    # Legacy compatibility fields
    phone = Column(String(20), nullable=True)
    dob = Column(Date, nullable=True)
    gender = Column(String(50), nullable=True)
    registration_number = Column(String(100), nullable=True)
    specialization = Column(String(100), nullable=True)
    qualification = Column(String(100), nullable=True)
    experience = Column(String(50), nullable=True)
    hospital = Column(String(255), nullable=True)
    college = Column(String(255), nullable=True)
    country = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    city = Column(String(100), nullable=True)

    analyses = relationship("Analysis", back_populates="user", cascade="all, delete-orphan")

    @property
    def password_hash(self) -> str:
        return self.hashed_password

    @password_hash.setter
    def password_hash(self, value: str):
        self.hashed_password = value
