import uuid
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import get_db
from app.models.user import User
from app.models.audit_log import AuditLog
from app.utils.security import hash_password, create_access_token

client = TestClient(app)


def cleanup_user(email: str):
    """Safely delete a test user and any referenced audit logs."""
    db = next(get_db())
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        db.query(AuditLog).filter(AuditLog.user_id == existing.id).delete(synchronize_session=False)
        db.delete(existing)
        db.commit()


def test_unauthenticated_protected_routes_return_401():
    """Verify that calling protected analysis routes without auth returns 401."""
    # Test GET priority queue
    res = client.get("/analysis/priority-queue")
    assert res.status_code == 401
    assert "Not authenticated" in res.json().get("detail", "")

    # Test GET samples
    res = client.get("/samples")
    assert res.status_code == 401

    # Test GET /auth/me without token
    res = client.get("/auth/me")
    assert res.status_code == 401

    # Test health check remains public
    res = client.get("/health")
    assert res.status_code == 200


def test_auth_signup_validation_and_success():
    """Verify signup validation rules and successful account creation."""
    # 1. Reject weak password (< 10 chars)
    weak_res = client.post("/auth/signup", json={
        "full_name": "Dr. Test Radiologist",
        "email": "test_radiologist@verifact.ai",
        "password": "short",
        "role": "radiologist"
    })
    assert weak_res.status_code == 422

    # 2. Reject password with no digits/special chars
    no_num_res = client.post("/auth/signup", json={
        "full_name": "Dr. Test Radiologist",
        "email": "test_radiologist@verifact.ai",
        "password": "allcharacterswithoutnumbers",
        "role": "radiologist"
    })
    assert no_num_res.status_code == 422

    # 3. Successful signup
    unique_email = f"test_signup_{uuid.uuid4().hex[:8]}@verifact.ai"
    cleanup_user(unique_email)

    try:
        signup_res = client.post("/auth/signup", json={
            "full_name": "Dr. Elena Vance",
            "email": unique_email,
            "password": "SecurePassword123!",
            "role": "radiologist",
            "institution": "Verifact Academic Medical Center",
            "department": "Diagnostic Radiology",
            "license_number": "RAD-88419-TX"
        })
        assert signup_res.status_code == 201
        data = signup_res.json()
        assert "access_token" in data
        assert data["user"]["email"] == unique_email
        assert data["user"]["full_name"] == "Dr. Elena Vance"
        assert data["user"]["role"] == "radiologist"

        # Verify cookie was set
        assert "access_token" in signup_res.cookies

        # 4. Reject duplicate email
        dup_res = client.post("/auth/signup", json={
            "full_name": "Dr. Impostor",
            "email": unique_email,
            "password": "SecurePassword123!",
            "role": "radiologist"
        })
        assert dup_res.status_code == 400
        assert "Email already registered" in dup_res.json()["detail"]
    finally:
        cleanup_user(unique_email)


def test_auth_login_flow_and_audit():
    """Verify login authentication, generic error on failure, and audit logging."""
    unique_email = f"test_login_{uuid.uuid4().hex[:8]}@verifact.ai"
    cleanup_user(unique_email)

    db = next(get_db())
    # Pre-seed user
    user = User(
        email=unique_email,
        hashed_password=hash_password("ValidPassword99!"),
        full_name="Dr. Login Specialist",
        role="resident",
        institution="Metropolitan Trauma Hospital"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    try:
        # 1. Failed login returns generic 400 error
        bad_login = client.post("/auth/login", json={
            "email": unique_email,
            "password": "WrongPassword99!"
        })
        assert bad_login.status_code == 400
        assert "Invalid email or password" in bad_login.json()["detail"]

        # Verify FAILED_LOGIN audit log was written
        failed_audit = db.query(AuditLog).filter(
            AuditLog.user_id == user.id,
            AuditLog.action == "FAILED_LOGIN"
        ).first()
        assert failed_audit is not None

        # 2. Successful login sets token & cookie
        login_res = client.post("/auth/login", json={
            "email": unique_email,
            "password": "ValidPassword99!"
        })
        assert login_res.status_code == 200
        login_data = login_res.json()
        assert "access_token" in login_data
        assert "access_token" in login_res.cookies

        # 3. Verify last_login_at updated
        db.refresh(user)
        assert user.last_login_at is not None

        # 4. Verify LOGIN audit log was written
        success_audit = db.query(AuditLog).filter(
            AuditLog.user_id == user.id,
            AuditLog.action == "LOGIN"
        ).first()
        assert success_audit is not None
    finally:
        cleanup_user(unique_email)


def test_profile_endpoints_and_change_password():
    """Verify GET/PATCH /auth/me and POST /auth/change-password."""
    unique_email = f"test_profile_{uuid.uuid4().hex[:8]}@verifact.ai"
    cleanup_user(unique_email)

    db = next(get_db())
    user = User(
        email=unique_email,
        hashed_password=hash_password("OriginalPassword10#"),
        full_name="Dr. Initial Name",
        role="radiologist",
        institution="City General"
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": unique_email})
    headers = {"Authorization": f"Bearer {token}"}

    try:
        # 1. GET /auth/me
        me_res = client.get("/auth/me", headers=headers)
        assert me_res.status_code == 200
        assert me_res.json()["email"] == unique_email
        assert me_res.json()["full_name"] == "Dr. Initial Name"

        # Also test via cookie
        client.cookies.set("access_token", token)
        me_cookie_res = client.get("/auth/me")
        assert me_cookie_res.status_code == 200
        assert me_cookie_res.json()["email"] == unique_email

        # 2. PATCH /auth/me
        patch_res = client.patch("/auth/me", headers=headers, json={
            "full_name": "Dr. Updated Name",
            "institution": "Stanford Health Care",
            "department": "Musculoskeletal Imaging",
            "license_number": "CA-MD-99120"
        })
        assert patch_res.status_code == 200
        updated = patch_res.json()
        assert updated["full_name"] == "Dr. Updated Name"
        assert updated["institution"] == "Stanford Health Care"
        assert updated["department"] == "Musculoskeletal Imaging"
        assert updated["license_number"] == "CA-MD-99120"

        # 3. POST /auth/change-password
        # Wrong old password
        wrong_change = client.post("/auth/change-password", headers=headers, json={
            "current_password": "WrongPassword123!",
            "new_password": "NewValidPassword77$"
        })
        assert wrong_change.status_code == 400
        assert "Current password is incorrect" in wrong_change.json()["detail"]

        # Valid change
        valid_change = client.post("/auth/change-password", headers=headers, json={
            "current_password": "OriginalPassword10#",
            "new_password": "NewValidPassword77$"
        })
        assert valid_change.status_code == 200
        assert valid_change.json()["status"] == "ok"

        # Test login with new password succeeds
        relogin = client.post("/auth/login", json={
            "email": unique_email,
            "password": "NewValidPassword77$"
        })
        assert relogin.status_code == 200

        # 4. POST /auth/logout
        logout_res = client.post("/auth/logout", headers=headers)
        assert logout_res.status_code == 200
    finally:
        cleanup_user(unique_email)
