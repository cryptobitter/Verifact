from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.schemas.auth_schema import (
    SignupRequest,
    UserResponse,
    LoginRequest,
    TokenResponse,
    VerifyOtpRequest,
    ProfileUpdateRequest
)
from app.utils.security import hash_password, verify_password, create_access_token, get_current_user
from app.services.email_services import generate_otp, get_otp_expiry, send_otp_email

router = APIRouter()


@router.post("/signup", response_model=UserResponse)
def signup(user_in: SignupRequest, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_in.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = hash_password(user_in.password)
    otp_code = generate_otp()
    otp_expires_at = get_otp_expiry()

    new_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        is_verified=True,
        otp_code=otp_code,
        otp_expires_at=otp_expires_at,
        full_name=user_in.full_name,
        phone=user_in.phone,
        dob=user_in.dob,
        gender=user_in.gender,
        registration_number=user_in.registration_number,
        specialization=user_in.specialization,
        qualification=user_in.qualification,
        experience=user_in.experience,
        hospital=user_in.hospital,
        college=user_in.college,
        department=user_in.department,
        country=user_in.country,
        state=user_in.state,
        city=user_in.city,
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    try:
        send_otp_email(new_user.email, otp_code)
    except Exception as exc:
        print(f"[WARN] Could not send OTP email ({exc}); account remains active.")

    return new_user


@router.post("/verify-otp", response_model=UserResponse)
def verify_otp(request: VerifyOtpRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # If already verified, return success — idempotent behaviour
    if user.is_verified:
        return user

    if user.otp_code != request.otp_code:
        raise HTTPException(status_code=400, detail="Invalid OTP code")

    if datetime.now(timezone.utc) > user.otp_expires_at:
        raise HTTPException(status_code=400, detail="OTP code has expired")

    user.is_verified = True
    user.otp_code = None
    user.otp_expires_at = None

    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=TokenResponse)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == login_data.email).first()

    if not user or not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )

    if not user.is_verified:
        user.is_verified = True
        db.commit()
        db.refresh(user)

    access_token = create_access_token(data={"sub": user.email})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.model_validate(user),
    )


@router.get("/me", response_model=UserResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user)
):
    return current_user


@router.put("/profile", response_model=UserResponse)
def update_profile(
    profile_data: ProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    current_user.full_name = profile_data.full_name
    current_user.phone = profile_data.phone
    if profile_data.specialization is not None:
        current_user.specialization = profile_data.specialization
    if profile_data.qualification is not None:
        current_user.qualification = profile_data.qualification
    if profile_data.experience is not None:
        current_user.experience = profile_data.experience
    if profile_data.hospital is not None:
        current_user.hospital = profile_data.hospital
    if profile_data.department is not None:
        current_user.department = profile_data.department
    if profile_data.country is not None:
        current_user.country = profile_data.country
    if profile_data.state is not None:
        current_user.state = profile_data.state
    if profile_data.city is not None:
        current_user.city = profile_data.city
    if profile_data.registration_number is not None:
        current_user.registration_number = profile_data.registration_number

    db.commit()
    db.refresh(current_user)
    return current_user