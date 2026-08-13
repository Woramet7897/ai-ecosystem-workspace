"""
main.py - FastAPI Application Entry Point
AI Ecosystem Backend

รัน: uvicorn main:app --reload
Docs: http://localhost:8000/docs
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.logger import setup_custom_logger
from core.database import create_all_tables
from core.minio_setup import ensure_buckets_exist
from features import inference, feedback, mlops, security
from features.auth import router as auth_router

logger = setup_custom_logger("main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup และ Shutdown events"""
    # ── Startup ──
    logger.info("Starting AI Ecosystem API...")
    try:
        create_all_tables()
        logger.info("PostgreSQL tables ready")
    except Exception as e:
        logger.error(f"PostgreSQL setup failed: {e}")

    try:
        ensure_buckets_exist()
        logger.info("MinIO buckets ready")
    except Exception as e:
        logger.error(f"MinIO setup failed: {e}")

    logger.info("AI Ecosystem API started - docs at http://localhost:8000/docs")
    yield
    # ── Shutdown ──
    logger.info("AI Ecosystem API shutting down...")


# ──────────────────────────────────────────────
# FastAPI App Instance
# ──────────────────────────────────────────────
app = FastAPI(
    title="AI Ecosystem API",
    description="""
## AI Ecosystem Backend API

ระบบ API หลักของ AI Ecosystem ออกแบบตาม Feature-Based Architecture
ประกอบด้วย 5 กลุ่ม:

| กลุ่ม | คำอธิบาย |
|---|---|
| **Authentication** | สมัครสมาชิก เข้าสู่ระบบ JWT token management |
| **Inference** | รับ input ส่งผ่านโมเดล AI แล้วคืนผลลัพธ์ |
| **Feedback** | รับ feedback และ export ข้อมูลจาก MinIO |
| **MLOps** | จัดการโมเดลและตรวจสอบสถานะระบบ |
| **Security** | ตรวจสอบ token และ usage quota |
    """,
    version="0.1.0",
    contact={"name": "Warintorn", "url": "https://github.com/Woramet7897/ai-ecosystem-workspace"},
    openapi_tags=[
        {"name": "Authentication", "description": "สมัครสมาชิก เข้าสู่ระบบ ต่ออายุ token"},
        {"name": "Inference",      "description": "ส่ง input เข้าโมเดล AI แล้วรับผลลัพธ์"},
        {"name": "Feedback",       "description": "รับ feedback และ export ข้อมูลจาก MinIO"},
        {"name": "MLOps",          "description": "จัดการโมเดลและตรวจสอบสถานะระบบ"},
        {"name": "Security",       "description": "ตรวจสอบ token และ rate limit"},
        {"name": "Root",           "description": "Health check เบื้องต้น"},
    ],
    lifespan=lifespan,
)

# ──────────────────────────────────────────────
# Middleware
# ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: จำกัด origin ก่อน deploy production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Include Routers (Feature-Based Architecture)
# ──────────────────────────────────────────────
app.include_router(auth_router.router)
app.include_router(inference.router)
app.include_router(feedback.router)
app.include_router(mlops.router)
app.include_router(security.router)


# ──────────────────────────────────────────────
# Root Endpoint
# ──────────────────────────────────────────────
@app.get(
    "/",
    tags=["Root"],
    summary="Health Check",
    description="ตรวจสอบว่า API ทำงานอยู่ คืน version และลิงก์ docs",
)
def root():
    return {
        "message": "AI Ecosystem API is running",
        "docs":    "http://localhost:8000/docs",
        "redoc":   "http://localhost:8000/redoc",
        "version": "0.1.0",
    }
