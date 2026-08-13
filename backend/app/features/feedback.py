"""
feedback.py - Data & Feedback API
ด้านที่ 2: รับ feedback จาก prediction แล้ว forward ไป Label Studio
และ export ข้อมูลจาก MinIO Object Storage

ช่วยสร้าง training loop: Predict → Feedback → Label → Retrain
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
import time

from core.config import settings
from core.logger import setup_custom_logger
from app.features.security import verify_token

logger = setup_custom_logger("feedback")

router = APIRouter(
    prefix="/feedback",
    tags=["Feedback"],
)

# ──────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────

class FeedbackRequest(BaseModel):
    """Schema สำหรับการส่ง feedback กลับมาหลัง prediction"""
    prediction_id:  str            = Field(..., description="ID ของ prediction ที่ต้องการส่ง feedback (ได้จาก /inference/predict)")
    correct_label:  str            = Field(..., description="label ที่ถูกต้องตามความเห็นของผู้ใช้")
    annotator_note: Optional[str]  = Field(None, description="หมายเหตุเพิ่มเติมจากผู้ annotate")
    send_to_label_studio: bool     = Field(False, description="ถ้า True จะ forward ข้อมูลนี้ไปสร้าง task ใน Label Studio อัตโนมัติ")

class FeedbackResponse(BaseModel):
    """Schema สำหรับ response หลังบันทึก feedback"""
    feedback_id:         str  = Field(..., description="ID ของ feedback ที่บันทึกเรียบร้อย")
    prediction_id:       str  = Field(..., description="ID ของ prediction ที่อ้างอิง")
    label_studio_task_id: Optional[int] = Field(None, description="Task ID ใน Label Studio ถ้ามีการส่งต่อ")
    message:             str  = Field(..., description="ข้อความยืนยัน")

class ExportRequest(BaseModel):
    """Schema สำหรับการ export ข้อมูลจาก MinIO"""
    bucket_name: str           = Field(..., description="ชื่อ bucket ใน MinIO ที่ต้องการ export")
    prefix:      Optional[str] = Field("", description="prefix สำหรับกรองไฟล์ เช่น 'images/2024/'")
    limit:       int           = Field(10, description="จำนวนไฟล์สูงสุดที่ต้องการ list")

class ExportResponse(BaseModel):
    """Schema สำหรับผลการ export จาก MinIO"""
    bucket_name: str       = Field(..., description="ชื่อ bucket ที่ export มา")
    prefix:      str       = Field(..., description="prefix ที่ใช้กรอง")
    objects:     List[str] = Field(..., description="รายการชื่อไฟล์ที่พบ")
    total:       int       = Field(..., description="จำนวนไฟล์ทั้งหมดที่พบ")


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.post(
    "/feedback",
    response_model=FeedbackResponse,
    summary="ส่ง Feedback หลังการประมวลผล",
    description="รับ feedback จากผลการ predict แล้วบันทึก และ forward ไป Label Studio ถ้าต้องการ",
)
def submit_feedback(req: FeedbackRequest, token: str = Depends(verify_token)):
    """
    POST /feedback/feedback

    รับ feedback หลังจากผู้ใช้เห็นผลการ predict และตรวจสอบความถูกต้อง
    ข้อมูลนี้จะถูกบันทึกไว้ใช้ใน Active Learning Loop

    การเชื่อมต่อจริง:
    - บันทึกลง PostgreSQL (TODO: ต่อด้วย SQLAlchemy)
    - ถ้า send_to_label_studio=True จะสร้าง Task ใน Label Studio ผ่าน SDK
      ใช้ config จาก settings.label_studio_url และ settings.label_studio_api_key

    [MOCK] ตอนนี้ยังไม่ได้ต่อกับ Label Studio จริง
    TODO: import LabelStudio SDK แล้วสร้าง Task จริง
    """
    logger.info(f"[feedback] prediction_id={req.prediction_id} label={req.correct_label} send_ls={req.send_to_label_studio}")

    feedback_id = f"fb_{int(time.time() * 1000)}"
    label_studio_task_id = None

    if req.send_to_label_studio:
        # ── [MOCK] Label Studio Integration ──
        # TODO: แทนที่ด้วยโค้ดจริง เช่น:
        #   from label_studio_sdk.client import LabelStudio
        #   ls = LabelStudio(base_url=settings.label_studio_url, api_key=settings.label_studio_api_key)
        #   task = ls.tasks.create(project=PROJECT_ID, data={"text": ..., "label": req.correct_label})
        #   label_studio_task_id = task.id
        logger.warning(f"[feedback] Label Studio integration is MOCK - URL={settings.label_studio_url}")
        label_studio_task_id = 9999  # MOCK task ID

    logger.info(f"[feedback] บันทึก feedback_id={feedback_id} เรียบร้อย")

    return FeedbackResponse(
        feedback_id=feedback_id,
        prediction_id=req.prediction_id,
        label_studio_task_id=label_studio_task_id,
        message="บันทึก feedback เรียบร้อย" + (" และส่งไป Label Studio แล้ว [MOCK]" if req.send_to_label_studio else ""),
    )


@router.post(
    "/export",
    response_model=ExportResponse,
    summary="ดึงรายการไฟล์จาก MinIO",
    description="List หรือ export ไฟล์จาก MinIO Object Storage ตาม bucket และ prefix ที่กำหนด",
)
def export_data(req: ExportRequest, token: str = Depends(verify_token)):
    """
    POST /feedback/export

    List ไฟล์ใน MinIO bucket ตาม prefix ที่กำหนด
    ใช้สำหรับ export ข้อมูลเพื่อนำไป train/validate โมเดล

    การเชื่อมต่อจริง:
    - ใช้ Minio client จาก library 'minio'
    - config มาจาก settings.minio_url, settings.minio_access_key, settings.minio_secret_key

    [CONNECTED] เชื่อมต่อ MinIO จริง
    จะ raise HTTPException ถ้า MinIO ไม่พร้อมใช้งาน
    """
    logger.info(f"[export] bucket={req.bucket_name} prefix='{req.prefix}' limit={req.limit}")

    try:
        from minio import Minio
        from minio.error import S3Error

        endpoint = settings.minio_url.replace("http://", "").replace("https://", "")
        client = Minio(
            endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=False,
        )

        if not client.bucket_exists(req.bucket_name):
            raise HTTPException(status_code=404, detail=f"Bucket '{req.bucket_name}' ไม่พบใน MinIO")

        objects = client.list_objects(req.bucket_name, prefix=req.prefix or "", recursive=True)
        object_names = []
        for i, obj in enumerate(objects):
            if i >= req.limit:
                break
            object_names.append(obj.object_name)

        logger.info(f"[export] พบ {len(object_names)} ไฟล์ใน bucket='{req.bucket_name}'")

        return ExportResponse(
            bucket_name=req.bucket_name,
            prefix=req.prefix or "",
            objects=object_names,
            total=len(object_names),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[export] MinIO error: {e}")
        raise HTTPException(status_code=503, detail=f"ไม่สามารถเชื่อมต่อ MinIO ได้: {str(e)}")
