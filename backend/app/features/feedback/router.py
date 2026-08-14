"""
feedback/router.py — APIRouter สำหรับ Feedback API endpoints

Endpoints:
  POST /feedback/submit    — ส่ง feedback แจ้งว่า prediction ผิด (ต้อง login)
  GET  /feedback/reviewed  — ดึง feedback ที่ expert ตรวจสอบแล้วจาก Label Studio (ต้อง login)
"""

from fastapi import APIRouter, Depends

from core.logger import setup_custom_logger
from app.features.auth.dependencies import get_current_active_user
from app.features.auth.models import User
from app.features.feedback.schemas import (
    FeedbackSubmitRequest,
    FeedbackSubmitResponse,
    ReviewedFeedbackResponse,
)
from app.features.feedback import service

logger = setup_custom_logger("feedback.router")

router = APIRouter(
    prefix="/feedback",
    tags=["Feedback"],
)


# ──────────────────────────────────────────────
# POST /feedback/submit
# ──────────────────────────────────────────────

@router.post(
    "/submit",
    response_model=FeedbackSubmitResponse,
    status_code=200,
    summary="ส่ง feedback แจ้งผลการทำนายที่ผิด",
    description="""
ผู้ใช้ส่ง feedback เพื่อแจ้งว่าผลการทำนายจาก `/inference/predict` ไม่ถูกต้อง
โดยระบุ label ที่ถูกต้องพร้อม prediction_id

**ต้องการ:** Bearer token จาก `/auth/login`

**Flow หลัง submit:**
1. ระบบสร้าง annotation task ใน Label Studio
2. Expert เปิด Label Studio เพื่อตรวจสอบและยืนยัน label
3. ข้อมูลที่ผ่านการตรวจแล้วใช้สำหรับ fine-tune โมเดลรุ่นถัดไป

**Error handling:**
- `503` — Label Studio ไม่พร้อมใช้งาน
- `502` — Label Studio ตอบกลับผิดพลาด
    """,
    response_description="ผลการส่ง feedback พร้อม feedback_id จาก Label Studio",
)
def submit_feedback(
    req: FeedbackSubmitRequest,
    current_user: User = Depends(get_current_active_user),
):
    logger.info(
        f"[submit] user={current_user.email} prediction_id={req.prediction_id}"
    )
    return service.submit_feedback(req, user_id=str(current_user.id))


# ──────────────────────────────────────────────
# GET /feedback/reviewed
# ──────────────────────────────────────────────

@router.get(
    "/reviewed",
    response_model=ReviewedFeedbackResponse,
    status_code=200,
    summary="ดึง feedback ที่ expert ตรวจสอบแล้ว",
    description="""
ดึงรายการ annotation ที่ expert ตรวจสอบและยืนยัน label เรียบร้อยแล้วจาก Label Studio

**ต้องการ:** Bearer token จาก `/auth/login`

**ใช้สำหรับ:**
- ทีม ML ดาวน์โหลดข้อมูลที่ผ่านการตรวจสอบไปใช้ fine-tune โมเดล
- ติดตามความคืบหน้าของการ annotate

**Error handling:**
- `503` — Label Studio ไม่พร้อมใช้งาน
- `502` — Label Studio ตอบกลับผิดพลาด
    """,
    response_description="รายการ annotation ที่ expert ตรวจสอบแล้ว พร้อมจำนวนทั้งหมด",
)
def get_reviewed_feedback(
    current_user: User = Depends(get_current_active_user),
):
    logger.info(f"[reviewed] user={current_user.email}")
    items = service.fetch_reviewed_feedback()
    return ReviewedFeedbackResponse(items=items, total=len(items))
