"""
core/database.py — SQLAlchemy engine + session dependency สำหรับ PostgreSQL

ทำหน้าที่เป็น infra client ชั้นเดียวที่คุยกับ PostgreSQL โดยตรง
feature อื่นๆ ใช้ get_db() ผ่าน Depends() เพื่อรับ session
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from typing import Generator

from core.config import settings

DATABASE_URL = (
    f"postgresql+psycopg://"
    f"{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}"
    f"/{settings.postgres_db}"
)

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class สำหรับ SQLAlchemy ORM models ทุกตัวในโปรเจกต์"""
    pass


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI Dependency — คืน database session ต่อ 1 request
    ใช้เป็น: db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_all_tables():
    """สร้างตารางทั้งหมดใน PostgreSQL (เรียกตอน startup)"""
    from features.auth.models import User  # noqa: F401 — import เพื่อให้ Base รู้จัก model
    Base.metadata.create_all(bind=engine)
