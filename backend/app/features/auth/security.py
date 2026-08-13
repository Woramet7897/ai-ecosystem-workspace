"""
auth/security.py - Password hashing & JWT token management
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from jose import JWTError, jwt

from core.config import settings  # อ่าน secret จาก .env ผ่าน core/config.py

# ── Config (อ่านจาก .env ผ่าน core/config.py ไม่ hardcode) ──
SECRET_KEY = settings.jwt_secret_key
ALGORITHM  = settings.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = 30   # access token หมดอายุ 30 นาที
REFRESH_TOKEN_EXPIRE_DAYS   = 7    # refresh token หมดอายุ 7 วัน


# ── Password hashing ──

def hash_password(plain_password: str) -> str:
    """Hash password ด้วย bcrypt (ปลอดภัย ไม่เก็บ plain text)"""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """ตรวจสอบ password กับ hash ที่เก็บใน database"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


# ── JWT Token ──

def create_access_token(data: dict) -> str:
    """
    สร้าง JWT Access Token
    - อายุ 30 นาที
    - ใช้เรียก API ทั่วไป
    """
    payload = data.copy()
    payload["type"] = "access"
    payload["exp"] = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(data: dict) -> str:
    """
    สร้าง JWT Refresh Token
    - อายุ 7 วัน
    - ใช้ขอ access token ใหม่เมื่อหมดอายุ
    """
    payload = data.copy()
    payload["type"] = "refresh"
    payload["exp"] = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """
    ถอดรหัส JWT Token
    คืน payload dict ถ้า valid, คืน None ถ้า invalid/หมดอายุ
    """
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
