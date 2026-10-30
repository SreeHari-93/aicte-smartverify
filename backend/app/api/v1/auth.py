from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from backend.app.config import settings
from backend.app.database import get_db
from backend.app.models.user import User, UserRole
from backend.app.models.institute import Institute
from backend.app.schemas.auth import (
    CaptchaResponse,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    TokenRefreshResponse,
    UserResponse,
    MessageResponse,
)
from backend.app.security.password import validate_password_policy, hash_password
from backend.app.security.csrf import (
    CSRF_COOKIE_NAME,
    CSRF_HEADER_NAME,
    require_csrf,
    verify_csrf_token,
)
from backend.app.services.auth_service import AuthService
from backend.app.services.audit_service import AuditService
from backend.app.api.deps import (
    get_current_user,
    ACCESS_TOKEN_COOKIE_NAME,
    REFRESH_TOKEN_COOKIE_NAME,
)

router = APIRouter(tags=["Authentication"])


def set_auth_cookies(
    response: Response,
    access_token: str,
    refresh_token: str,
    csrf_token: str,
):
    """Set secure HTTP-only cookies for tokens and readable cookie for CSRF"""
    # Access token cookie (15 min)
    response.set_cookie(
        key=ACCESS_TOKEN_COOKIE_NAME,
        value=access_token,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )
    # Refresh token cookie (7 days)
    response.set_cookie(
        key=REFRESH_TOKEN_COOKIE_NAME,
        value=refresh_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )
    # CSRF cookie (readable by frontend script for double submit)
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        path="/",
    )


def clear_auth_cookies(response: Response):
    """Clear all authentication cookies"""
    response.delete_cookie(key=ACCESS_TOKEN_COOKIE_NAME, path="/")
    response.delete_cookie(key=REFRESH_TOKEN_COOKIE_NAME, path="/")
    response.delete_cookie(key=CSRF_COOKIE_NAME, path="/")


@router.get("/captcha", response_model=CaptchaResponse)
def get_captcha(db: Session = Depends(get_db)):
    """
    Generate dynamic distorted image captcha.
    Stores SHA-256 hash with 2-minute TTL.
    """
    captcha_id, image_base64 = AuthService.create_captcha(db)
    return CaptchaResponse(captcha_id=captcha_id, image_base64=image_base64)


@router.post("/login", response_model=LoginResponse)
def login(
    login_data: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """
    Authenticate Institute or Admin user with constant-time verification,
    captcha validation, rate limiting, and account lockout protection.
    Sets HttpOnly cookies on success.
    """
    ip_address, user_agent = AuditService.extract_client_info(request)

    user, access_token, refresh_token, csrf_token = AuthService.authenticate_user(
        db=db,
        role=login_data.role,
        password=login_data.password,
        captcha_id=login_data.captcha_id,
        captcha_text=login_data.captcha_text,
        ip_address=ip_address,
        user_agent=user_agent,
        institute_id=login_data.institute_id,
        institute_name=login_data.institute_name,
        identifier=login_data.identifier,
    )

    set_auth_cookies(response, access_token, refresh_token, csrf_token)

    return LoginResponse(
        message="Login successful",
        user=user,
        csrf_token=csrf_token,
    )


@router.post("/logout", response_model=MessageResponse)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Revoke refresh token and clear all auth cookies"""
    ip_address, user_agent = AuditService.extract_client_info(request)
    raw_refresh = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)

    # Optional user identification from access token
    user_id = None
    access_cookie = request.cookies.get(ACCESS_TOKEN_COOKIE_NAME)
    if access_cookie:
        from backend.app.security.tokens import decode_access_token

        payload = decode_access_token(access_cookie)
        if payload and "sub" in payload:
            user_id = int(payload["sub"])

    AuthService.logout(
        db=db,
        raw_refresh_token=raw_refresh,
        user_id=user_id,
        ip_address=ip_address,
        user_agent=user_agent,
    )

    clear_auth_cookies(response)
    return MessageResponse(message="Logged out successfully")


@router.post("/refresh", response_model=TokenRefreshResponse)
def refresh_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Rotate refresh token and issue new access token"""
    raw_refresh = request.cookies.get(REFRESH_TOKEN_COOKIE_NAME)
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token missing from cookies.",
        )

    user, new_access, new_refresh, new_csrf = AuthService.refresh_access_token(
        db=db, raw_refresh_token=raw_refresh
    )

    set_auth_cookies(response, new_access, new_refresh, new_csrf)
    return TokenRefreshResponse(
        message="Token refreshed successfully",
        csrf_token=new_csrf,
    )


@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """Retrieve details of currently authenticated user and institute"""
    return current_user


@router.post("/register", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def register(
    data: RegisterRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Registration stub with strong validation and password policy.
    Supports Institute and Admin self-service registration onboarding.
    """
    # 1. Validate password policy
    is_valid, msg = validate_password_policy(data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=msg,
        )

    # 2. Check if email already registered
    existing_user = db.query(User).filter(User.email.ilike(data.email.strip())).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists.",
        )

    institute_obj = None
    if data.role == UserRole.INSTITUTE:
        inst_id = (data.aicte_institute_id or "").strip().upper()
        if not inst_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Institute ID is required for institute registration.",
            )

        existing_inst = (
            db.query(Institute).filter(Institute.aicte_institute_id == inst_id).first()
        )
        if existing_inst:
            institute_obj = existing_inst
        else:
            institute_obj = Institute(
                aicte_institute_id=inst_id,
                name=data.institute_name or f"Institute {inst_id}",
                state=data.state or "National",
                status="PENDING_VERIFICATION",
            )
            db.add(institute_obj)
            db.commit()
            db.refresh(institute_obj)

    # 3. Create user
    new_user = User(
        email=data.email.strip().lower(),
        password_hash=hash_password(data.password),
        role=data.role,
        institute_id=institute_obj.id if institute_obj else None,
        is_active=True,
    )
    db.add(new_user)
    db.commit()

    ip_address, user_agent = AuditService.extract_client_info(request)
    AuditService.log_event(
        db=db,
        action="REGISTER",
        user_id=new_user.id,
        role=new_user.role,
        ip_address=ip_address,
        user_agent=user_agent,
        reason="New user registered",
    )

    return MessageResponse(message="Account registered successfully. Please proceed to login.")

