"""
main.py - FastAPI Application Entry Point
AI Ecosystem Backend

รัน: uvicorn main:app --reload
Docs: http://localhost:8000/docs
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.logger import setup_custom_logger
from features import inference, feedback, mlops, security
from features.auth import router as auth_router
from features.auth.database import create_tables

logger = setup_custom_logger("main")

# ──────────────────────────────────────────────
# FastAPI App Instance
# ──────────────────────────────────────────────
app = FastAPI(
    title="AI Ecosystem API",
    description="""
## AI Ecosystem Backend API

ระบบ API หลักของ AI Ecosystem ประกอบด้วย 4 กลุ่ม:

| กลุ่ม | คำอธิบาย |
|---|---|
| **Inference** | รับ input ส่งผ่านโมเดล AI แล้วคืนผลลัพธ์ |
| **Feedback** | รับ feedback และ export ข้อมูลจาก MinIO |
| **MLOps** | จัดการโมเดลและตรวจสอบสถานะระบบ |
| **Security** | ตรวจสอบ token และ usage quota |
    """,
    version="0.1.0",
    contact={"name": "Warintorn", "url": "https://github.com/Woramet7897/ai-ecosystem-workspace"},
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
app.include_router(inference.router)
app.include_router(feedback.router)
app.include_router(mlops.router)
app.include_router(security.router)
app.include_router(auth_router.router)

# สร้างตาราง users ใน PostgreSQL อัตโนมัติเมื่อ server เริ่มต้น
create_tables()

logger.info("AI Ecosystem API started - docs at http://localhost:8000/docs")

# ──────────────────────────────────────────────
# Root Endpoint
# ──────────────────────────────────────────────
@app.get("/", tags=["Root"], summary="Root", description="หน้าแรก ตรวจสอบว่า API ทำงานอยู่")
def root():
    return {
        "message": "AI Ecosystem API is running",
        "docs": "http://localhost:8000/docs",
        "version": "0.1.0",
    }
