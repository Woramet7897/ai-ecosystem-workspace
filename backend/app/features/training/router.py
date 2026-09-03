"""
training/router.py - Training Queue API endpoints

Endpoints:
  POST /training/queue            — ส่ง training job เข้า Redis queue พร้อมกำหนดเวลาเริ่ม
  GET  /training/queue/{job_id}   — เช็คสถานะของ training job
"""

from fastapi import APIRouter, Depends

from core.logger import setup_custom_logger
from app.features.auth.dependencies import get_current_active_user
from app.features.auth.models import User
from app.features.training.schemas import (
    TrainQueueRequest,
    TrainQueueResponse,
    TrainStatusResponse,
)
from app.features.training import service

logger = setup_custom_logger("training.router")

router = APIRouter(
    prefix="/training",
    tags=["Training"],
)


@router.post(
    "/queue",
    response_model=TrainQueueResponse,
    status_code=202,
    summary="ส่ง Training Job เข้าคิว",
    description="""
ส่งคำขอ fine-tune โมเดล Token Classification เข้า Redis queue

**`start_time`** คือเวลาที่ต้องการให้ Worker เริ่มทำงานจริง
Job จะอยู่สถานะ `deferred` จนถึงเวลานั้น (ARQ `_defer_until`)

**Flow หลัง submit:**
1. FastAPI รับ request แล้วส่ง job เข้า Redis ทันที
2. Job อยู่สถานะ `deferred` จนถึง `start_time`
3. Trainer Worker หยิบงานมาทำ: โหลด dataset จาก MinIO → เทรน → อัปโหลดโมเดลกลับ MinIO
4. ตรวจสอบสถานะได้ผ่าน GET /training/queue/{job_id}

**ต้องการ:** Bearer token จาก `/auth/login`
    """,
    response_description="Job ID สำหรับติดตามสถานะ",
)
async def queue_training(
    req: TrainQueueRequest,
    current_user: User = Depends(get_current_active_user),
):
    logger.info(
        f"[queue] user={current_user.email} dataset={req.dataset_name} "
        f"model={req.model_name} start={req.start_time}"
    )
    return await service.enqueue_training(req, user_id=str(current_user.id))


@router.get(
    "/queue/{job_id}",
    response_model=TrainStatusResponse,
    summary="เช็คสถานะ Training Job",
    description="""
ดึงสถานะปัจจุบันของ training job จาก Redis

**สถานะที่เป็นไปได้:**
- `deferred` — รอถึงเวลา start_time
- `queued` — รอ worker ว่าง
- `in_progress` — กำลังเทรนอยู่
- `complete` — เสร็จแล้ว ดู result สำหรับ summary
- `not_found` — ไม่พบ job (หมดอายุหรือ ID ผิด)
- `aborted` — ถูกยกเลิก

**ต้องการ:** Bearer token จาก `/auth/login`
    """,
)
async def get_job_status(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
):
    logger.info(f"[status] user={current_user.email} job_id={job_id}")
    return await service.get_training_status(job_id)
