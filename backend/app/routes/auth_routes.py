from collections import defaultdict
from datetime import datetime, timezone
import time
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.auth_schema import (
    SignupRequest,
    UserResponse,
    LoginRequest,
    TokenResponse,
    ProfileUpdateRequest,
    ChangePasswordRequest
)
from app.utils.security import (
    hash_password,
    verify_password,
    create_access_token,
    set_auth_cookie,
    clear_auth_cookie,
    get_current_user
)

router = APIRouter()

# In-memory sliding window rate limiter: 5 attempts per 60s per IP for auth routes
_auth_rate_limits = defaultdict(list)
RATE_LIMIT_WINDOW_SEC = 60
MAX_AUTH_ATTEMPTS = 5


def check_auth_rate_limit(request: Request):
    client_ip = request.client.host if request.client else "127.0.0.1"
    now = time.time()
    # Filter attempts within window
    _auth_rate_limits[client_ip] = [
        t for t in _auth_rate_limits[client_ip] if now - t < RATE_LIMIT_WINDOW_SEC
    ]
    if len(_auth_rate_limits[client_ip]) >= MAX_AUTH_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many authentication attempts. Please try again in 1 minute."
        )
    _auth_rate_limits[client_ip].append(now)
    return client_ip


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(
    user_in: SignupRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    client_ip = check_auth_rate_limit(request)

    normalized_email = user_in.email.strip().lower()
    existing_user = db.query(User).filter(User.email == normalized_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_pw = hash_password(user_in.password)
    institution_val = user_in.institution or user_in.hospital or "Verifact Health"
    license_val = user_in.license_number or user_in.registration_number or ""

    new_user = User(
        email=normalized_email,
        hashed_password=hashed_pw,
        is_verified=True,
        full_name=user_in.full_name,
        role=user_in.role or "radiologist",
        institution=institution_val,
        hospital=institution_val,
        department=user_in.department or "Diagnostic Radiology",
        license_number=license_val,
        registration_number=license_val,
        phone=user_in.phone,
        specialization=user_in.specialization,
        qualification=user_in.qualification,
        experience=user_in.experience,
        college=user_in.college,
        country=user_in.country,
        state=user_in.state,
        city=user_in.city,
        last_login_at=datetime.now(timezone.utc)
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    # Record Audit Log
    audit = AuditLog(
        user_id=new_user.id,
        action="SIGNUP",
        details=f"Physician account created for {new_user.full_name} ({new_user.role})",
        ip_address=client_ip
    )
    db.add(audit)
    db.commit()

    # Issue token & set httpOnly cookie
    token = create_access_token(data={"sub": new_user.email})
    set_auth_cookie(response, token)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(new_user)
    )


@router.post("/login", response_model=TokenResponse)
def login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    client_ip = check_auth_rate_limit(request)
    normalized_email = login_data.email.strip().lower()

    user = db.query(User).filter(User.email == normalized_email).first()

    if not user or not verify_password(login_data.password, user.hashed_password):
        # Generic error message to prevent user enumeration
        audit = AuditLog(
            user_id=user.id if user else None,
            action="FAILED_LOGIN",
            details="Failed sign-in attempt (invalid credentials)",
            ip_address=client_ip
        )
        db.add(audit)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email or password"
        )

    # Update last login timestamp
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    # Log successful login
    audit = AuditLog(
        user_id=user.id,
        action="LOGIN",
        details="User authenticated successfully",
        ip_address=client_ip
    )
    db.add(audit)
    db.commit()

    token = create_access_token(data={"sub": user.email})
    set_auth_cookie(response, token)

    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user=UserResponse.model_validate(user)
    )


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    client_ip = get_client_ip(request)
    clear_auth_cookie(response)

    # Attempt to log logout if token exists
    try:
        from app.utils.security import get_current_user
        # Optional check: do not block logout if already invalid
        cookie_token = request.cookies.get("access_token")
        if cookie_token:
            from jose import jwt
            from app.config import settings
            payload = jwt.decode(cookie_token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            user = db.query(User).filter(User.email == payload.get("sub")).first()
            if user:
                audit = AuditLog(
                    user_id=user.id,
                    action="LOGOUT",
                    details="User signed out",
                    ip_address=client_ip
                )
                db.add(audit)
                db.commit()
    except Exception:
        pass

    return {"status": "ok", "message": "Successfully logged out"}


@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user


@router.patch("/me", response_model=UserResponse)
def update_profile(
    profile_data: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if profile_data.full_name is not None:
        current_user.full_name = profile_data.full_name.strip()
    if profile_data.institution is not None:
        current_user.institution = profile_data.institution.strip()
        current_user.hospital = profile_data.institution.strip()
    elif profile_data.hospital is not None:
        current_user.institution = profile_data.hospital.strip()
        current_user.hospital = profile_data.hospital.strip()

    if profile_data.department is not None:
        current_user.department = profile_data.department.strip()

    if profile_data.license_number is not None:
        current_user.license_number = profile_data.license_number.strip()
        current_user.registration_number = profile_data.license_number.strip()
    elif profile_data.registration_number is not None:
        current_user.license_number = profile_data.registration_number.strip()
        current_user.registration_number = profile_data.registration_number.strip()

    if profile_data.phone is not None:
        current_user.phone = profile_data.phone.strip()
    if profile_data.specialization is not None:
        current_user.specialization = profile_data.specialization.strip()
    if profile_data.qualification is not None:
        current_user.qualification = profile_data.qualification.strip()
    if profile_data.experience is not None:
        current_user.experience = profile_data.experience.strip()

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    client_ip = get_client_ip(request)

    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    current_user.hashed_password = hash_password(data.new_password)
    db.commit()

    audit = AuditLog(
        user_id=current_user.id,
        action="PASSWORD_CHANGE",
        details="User changed account password",
        ip_address=client_ip
    )
    db.add(audit)
    db.commit()

    return {"status": "ok", "message": "Password updated successfully"}
