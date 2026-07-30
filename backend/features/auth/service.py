"""
auth/service.py - Business logic สำหรับ User management
"""

import uuid
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from features.auth.models import User
from features.auth.security import hash_password, verify_password


def is_email_or_username_taken(db: Session, email: str, username: str) -> Optional[str]:
    """
    ตรวจสอบว่า email หรือ username ถูกใช้ไปแล้วหรือยัง
    คืน 'email' หรือ 'username' ถ้าซ้ำ, คืน None ถ้าใช้ได้
    """
    existing = db.query(User).filter(
        or_(User.email == email, User.username == username)
    ).first()

    if existing is None:
        return None
    if existing.email == email:
        return "email"
    return "username"


def create_user(db: Session, email: str, username: str, password: str, full_name: Optional[str] = None) -> User:
    """
    สร้าง User ใหม่ใน database
    - Hash password ด้วย bcrypt ก่อนบันทึก (ไม่เก็บ plain text)
    - บันทึกลง PostgreSQL
    """
    user = User(
        email=email,
        username=username,
        hashed_password=hash_password(password),
        full_name=full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """
    ตรวจสอบ email + password
    คืน User object ถ้าถูกต้อง, คืน None ถ้าผิด
    """
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def get_user_by_id(db: Session, user_id: uuid.UUID) -> Optional[User]:
    """ดึง User จาก database โดยใช้ ID"""
    return db.query(User).filter(User.id == user_id).first()
