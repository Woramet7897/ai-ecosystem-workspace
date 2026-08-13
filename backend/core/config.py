"""
core/config.py — โหลด environment variables ทั้งหมดจาก .env ผ่าน pydantic-settings
เป็นแหล่งข้อมูล config เดียวของระบบ — ทุก module import settings จากที่นี่
"""

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # ── PostgreSQL ──
    postgres_user: str
    postgres_password: str
    postgres_db: str
    postgres_host: str
    postgres_port: int

    # ── Redis ──
    redis_host: str
    redis_port: int

    # ── MinIO ──
    minio_url: str
    minio_access_key: str
    minio_secret_key: str

    # ── Label Studio ──
    label_studio_url: str
    label_studio_api_key: str

    # ── JWT ──
    # สร้างค่าใหม่ด้วย: python -c "import secrets; print(secrets.token_hex(32))"
    # ห้ามใช้ค่า default หรือค่าที่เคย commit ขึ้น git
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"  # default แต่ override ได้ใน .env

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

settings = Settings()