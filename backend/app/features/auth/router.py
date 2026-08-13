"""
auth/router.py - API endpoints สำหรับ Sign-up / Login / Logout / Refresh / Me
"""

import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.database import get_db
from app.features.auth.dependencies import get_current_active_user
from app.features.auth.models import User
from app.features.auth.schemas import (
    LoginRequest, MessageResponse, RefreshTokenRequest,
    SignUpRequest, TokenResponse, UserResponse,
)
from app.features.auth.security import (
    create_access_token, create_refresh_token, decode_token,
)
from app.features.auth.service import (
    authenticate_user, create_user, get_user_by_id, is_email_or_username_taken,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ─────────────────────────────────────────────
@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="สมัครสมาชิกใหม่",
)
def signup(body: SignUpRequest, db: Session = Depends(get_db)):
    """
    POST /auth/signup

    สร้างบัญชีผู้ใช้ใหม่
    - ตรวจสอบ email / username ซ้ำ
    - Hash password ด้วย bcrypt (ปลอดภัย)
    - บันทึกลง PostgreSQL
    """
    taken = is_email_or_username_taken(db, body.email, body.username)
    if taken == "email":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="อีเมลนี้ถูกใช้งานแล้ว")
    if taken == "username":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ชื่อผู้ใช้นี้ถูกใช้งานแล้ว")

    user = create_user(db, email=body.email, username=body.username, password=body.password, full_name=body.full_name)
    return _user_to_response(user)


# ─────────────────────────────────────────────
@router.post(
    "/login",
    response_model=TokenResponse,
    summary="เข้าสู่ระบบ - รับ JWT Token",
)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    """
    POST /auth/login

    ตรวจสอบ email + password แล้วออก JWT token คู่:
    - **access_token**: อายุ 30 นาที ใช้เรียก API ทั่วไป
    - **refresh_token**: อายุ 7 วัน ใช้ขอ token ใหม่
    """
    user = authenticate_user(db, email=body.email, password=body.password)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="อีเมลหรือรหัสผ่านไม่ถูกต้อง")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="บัญชีนี้ถูกระงับการใช้งาน")

    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


# ─────────────────────────────────────────────
@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="ออกจากระบบ",
)
def logout(_current_user: User = Depends(get_current_active_user)):
    """
    POST /auth/logout

    ออกจากระบบ — ยืนยันว่า token ยัง valid ก่อนตอบ
    (Stateless JWT: client ควรลบ token ออกจาก storage เอง)
    """
    return MessageResponse(message="ออกจากระบบเรียบร้อย")


# ─────────────────────────────────────────────
@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="ต่ออายุ Token",
)
def refresh_token(body: RefreshTokenRequest, db: Session = Depends(get_db)):
    """
    POST /auth/refresh

    ใช้ refresh_token เพื่อขอ token คู่ใหม่
    - ตรวจสอบว่า refresh token ยัง valid
    - ออก access + refresh token ใหม่ทั้งคู่ (token rotation)
    """
    payload = decode_token(body.refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token ไม่ถูกต้องหรือหมดอายุ")

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ไม่มีข้อมูลผู้ใช้")

    user = get_user_by_id(db, uuid.UUID(user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="ไม่พบผู้ใช้หรือบัญชีถูกระงับ")

    return TokenResponse(
        access_token=create_access_token(data={"sub": str(user.id)}),
        refresh_token=create_refresh_token(data={"sub": str(user.id)}),
    )


# ─────────────────────────────────────────────
@router.get(
    "/me",
    response_model=UserResponse,
    summary="ดูข้อมูลผู้ใช้ปัจจุบัน",
)
def get_me(current_user: User = Depends(get_current_active_user)):
    """
    GET /auth/me

    ดึงข้อมูล user ที่กำลัง login อยู่
    ต้องส่ง access_token ใน Header: Authorization: Bearer <token>
    """
    return _user_to_response(current_user)


# ── Helper ──
def _user_to_response(user: User) -> UserResponse:
    """แปลง User ORM model → UserResponse schema"""
    return UserResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        bio=user.bio,
        is_active=user.is_active,
        created_at=user.created_at,
        updated_at=user.updated_at,
    )
