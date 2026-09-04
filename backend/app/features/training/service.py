"""
training/service.py - Business logic for Training Queue

ทำหน้าที่:
1. enqueue_training() — ส่ง job เข้า ARQ Redis queue พร้อม _defer_until
2. get_training_status() — ดึงสถานะ job จาก ARQ
"""

from datetime import timezone
from arq import create_pool
from arq.jobs import Job, JobStatus

from core.redis_client import get_arq_redis_settings
from core.logger import setup_custom_logger
from app.features.training.schemas import TrainQueueRequest, TrainQueueResponse, TrainStatusResponse

logger = setup_custom_logger("training.service")


async def enqueue_training(req: TrainQueueRequest, user_id: str) -> TrainQueueResponse:
    """
    ส่ง training job เข้า ARQ queue พร้อม _defer_until=req.start_time

    _defer_until ทำให้ ARQ worker ไม่หยิบงานมาทำจนกว่าจะถึงเวลาที่กำหนด
    ทำให้คิวมี "เวลาเริ่มทำงานที่กำหนดได้" ตาม requirement

    Args:
        req:     TrainQueueRequest พร้อม start_time
        user_id: UUID ของ user ที่ส่งคำขอ
    """
    pool = await create_pool(get_arq_redis_settings())

    # ARQ ต้องการ timezone-aware datetime สำหรับ _defer_until
    start_time_utc = req.start_time
    if start_time_utc.tzinfo is None:
        start_time_utc = start_time_utc.replace(tzinfo=timezone.utc)

    job = await pool.enqueue_job(
        "train_model",
        req.dataset_name,
        req.model_name,
        req.base_model,
        req.num_epochs,
        req.batch_size,
        req.max_steps,
        user_id,
        _defer_until=start_time_utc,
    )

    await pool.aclose()

    job_id = job.job_id if job else "unknown"
    logger.info(
        f"[enqueue] job_id={job_id} dataset={req.dataset_name} "
        f"model={req.model_name} start_time={req.start_time} user={user_id}"
    )

    return TrainQueueResponse(
        job_id=job_id,
        model_name=req.model_name,
        dataset_name=req.dataset_name,
        status="deferred",
        start_time=req.start_time,
        message=f"Training job queued. Worker will start at {req.start_time.isoformat()}",
    )


async def get_training_status(job_id: str) -> TrainStatusResponse:
    """
    ดึงสถานะของ ARQ job โดยตรงจาก Redis

    ARQ JobStatus values: deferred, queued, in_progress, complete, not_found, aborted
    """
    pool = await create_pool(get_arq_redis_settings())
    job = Job(job_id, pool)

    try:
        status = await job.status()
        info = await job.info()

        status_str = status.value if isinstance(status, JobStatus) else str(status)

        result = None
        if status == JobStatus.complete:
            try:
                result = await job.result(timeout=1)
            except Exception:
                result = "completed (result not available)"

        await pool.aclose()

        return TrainStatusResponse(
            job_id=job_id,
            status=status_str,
            result=result,
            enqueue_time=info.enqueue_time.isoformat() if info and info.enqueue_time else None,
            start_time=info.start_time.isoformat() if info and info.start_time else None,
            finish_time=info.finish_time.isoformat() if info and info.finish_time else None,
        )

    except Exception as e:
        logger.warning(f"[status] job_id={job_id} error={e}")
        await pool.aclose()
        return TrainStatusResponse(
            job_id=job_id,
            status="not_found",
            result=None,
            enqueue_time=None,
            start_time=None,
            finish_time=None,
        )
