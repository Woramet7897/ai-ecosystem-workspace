"""
auth/schemas.py - Pydantic request/response models สำหรับ Authentication
"""

import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field
from typing import Optional


# ── Requests ──

class SignUpRequest(BaseModel):
    """สมัครสมาชิกใหม่"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    password: str = Field(..., min_length=8, max_length=128)
    full_name: Optional[str] = Field(None, max_length=255)

    class Config:
        json_schema_extra = {
            "example": {
                "email": "warintorn@example.com",
                "username": "warintorn",
                "password": "mypassword123",
                "full_name": "Warintorn"
            }
        }


class LoginRequest(BaseModel):
    """เข้าสู่ระบบ"""
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "warintorn@example.com",
                "password": "mypassword123"
            }
        }


class RefreshTokenRequest(BaseModel):
    """ต่ออายุ token"""
    refresh_token: str


# ── Responses ──

class TokenResponse(BaseModel):
    """Token pair ที่ได้หลัง login"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """ข้อมูลผู้ใช้ (ไม่รวม password)"""
    id: uuid.UUID
    email: str
    username: str
    full_name: Optional[str] = None
    bio: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class MessageResponse(BaseModel):
    """Response ข้อความทั่วไป"""
    message: str
