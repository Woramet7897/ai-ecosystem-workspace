"""
auth/dependencies.py - FastAPI Dependencies สำหรับดึง current user จาก JWT token
"""

import uuid
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from features.auth.database import get_db
from features.auth.models import User
from features.auth.security import decode_token
from features.auth.service import get_user_by_id

# ใช้ HTTPBearer ทำให้ Swagger UI แสดงปุ่ม Authorize และรับ Bearer token ได้ถูกต้อง
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Dependency: ดึง User ปัจจุบันจาก JWT access token
    ใช้เป็น Depends(get_current_user) ใน endpoint ที่ต้องการล็อกอิน
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="กรุณา Login ก่อนใช้งาน",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_token(credentials.credentials)
    if payload is None or payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token ไม่ถูกต้องหรือหมดอายุ กรุณา Login ใหม่",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token ไม่มีข้อมูลผู้ใช้")

    user = get_user_by_id(db, uuid.UUID(user_id_str))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="ไม่พบผู้ใช้ในระบบ")

    return user


def get_current_active_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Dependency: ตรวจสอบว่า user ที่ login อยู่ยังไม่ถูกระงับ
    ใช้เป็น Depends(get_current_active_user) ใน endpoint สำคัญ
    """
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="บัญชีนี้ถูกระงับการใช้งาน")
    return current_user
