from datetime import datetime, date
from typing import Optional, Literal
import re
from pydantic import BaseModel, Field, EmailStr, field_validator


def validate_password_strength(v: str) -> str:
    if len(v) < 10:
        raise ValueError("Password must be at least 10 characters long")
    if not any(char.isdigit() for char in v) and not any(not char.isalnum() for char in v):
        raise ValueError("Password must contain at least one number or special character")
    if not any(char.isalpha() for char in v):
        raise ValueError("Password must contain at least one letter")
    return v


class SignupRequest(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=10)
    role: Literal["radiologist", "resident", "admin", "physician"] = "radiologist"
    institution: Optional[str] = None
    department: Optional[str] = None
    license_number: Optional[str] = None

    # Legacy fields
    hospital: Optional[str] = None
    registration_number: Optional[str] = None
    phone: Optional[str] = None
    dob: Optional[date] = None
    gender: Optional[str] = None
    specialization: Optional[str] = None
    qualification: Optional[str] = None
    experience: Optional[str] = None
    college: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.strip().lower()


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=10)

    @field_validator("new_password")
    @classmethod
    def check_password(cls, v: str) -> str:
        return validate_password_strength(v)


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    institution: Optional[str] = None
    department: Optional[str] = None
    license_number: Optional[str] = None

    # Legacy fields
    phone: Optional[str] = None
    specialization: Optional[str] = None
    qualification: Optional[str] = None
    experience: Optional[str] = None
    hospital: Optional[str] = None
    registration_number: Optional[str] = None
    country: Optional[str] = None
    state: Optional[str] = None
    city: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: Optional[str] = None
    role: str = "radiologist"
    institution: Optional[str] = None
    department: Optional[str] = None
    license_number: Optional[str] = None
    created_at: Optional[datetime] = None
    last_login_at: Optional[datetime] = None

    # Legacy compatibility
    hospital: Optional[str] = None
    registration_number: Optional[str] = None
    phone: Optional[str] = None
    specialization: Optional[str] = None
    is_verified: bool = True

    model_config = {
        "from_attributes": True
    }


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Optional[UserResponse] = None


class VerifyOtpRequest(BaseModel):
    email: EmailStr
    otp_code: str = Field(..., min_length=6, max_length=6)
