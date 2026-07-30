"""
auth/database.py - PostgreSQL connection & session management
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from core.config import settings
from features.auth.models import Base

# สร้าง connection string จาก settings
DATABASE_URL = (
    f"postgresql+psycopg://"
    f"{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}"
    f"/{settings.postgres_db}"
)

engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def create_tables():
    """สร้างตาราง users ใน database (ถ้ายังไม่มี)"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency สำหรับ FastAPI
    ใช้เป็น Depends(get_db) ใน endpoint ที่ต้องการ database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
