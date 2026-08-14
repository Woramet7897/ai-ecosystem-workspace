"""
feedback/service.py — Business logic สำหรับ Feedback feature

ทำหน้าที่เป็นตัวกลางระหว่าง router และ core/label_studio_tasks.py
จัดการ error ก่อนที่จะโยน HTTPException ขึ้นไปให้ router
"""

import uuid
import requests.exceptions
from fastapi import HTTPException, status

from core.config import settings
from core.label_studio_tasks import create_feedback_task, get_completed_annotations
from core.logger import setup_custom_logger
from app.features.feedback.schemas import (
    FeedbackSubmitRequest,
    FeedbackSubmitResponse,
    ReviewedFeedbackItem,
)

logger = setup_custom_logger("feedback.service")

# อ่าน project_id จาก config (ไม่ hardcode)
FEEDBACK_PROJECT_ID = settings.label_studio_feedback_project_id


def submit_feedback(req: FeedbackSubmitRequest, user_id: str) -> FeedbackSubmitResponse:
    """
    ส่ง feedback เข้า Label Studio เป็น annotation task

    Flow:
    1. เรียก core/label_studio_tasks.create_feedback_task()
    2. ถ้า Label Studio ไม่พร้อม → catch error → คืน HTTPException 503
    3. log การส่ง feedback ทุกครั้ง

    Args:
        req:     FeedbackSubmitRequest จาก router
        user_id: UUID ของ user ที่ส่ง feedback

    Returns:
        FeedbackSubmitResponse พร้อม feedback_id และ status
    """
    logger.info(
        f"[submit] user={user_id} prediction_id={req.prediction_id} "
        f"predicted='{req.predicted_label}' correct='{req.correct_label}'"
    )

    try:
        result = create_feedback_task(
            project_id=FEEDBACK_PROJECT_ID,
            prediction_id=req.prediction_id,
            input_text=req.input_text,
            predicted_label=req.predicted_label,
            correct_label=req.correct_label,
        )

        # Label Studio คืน dict ที่มี imported task count หรือ task list
        # ดึง task_id ออกมาถ้ามี
        task_id = _extract_task_id(result, req.prediction_id)

        logger.info(f"[submit] success feedback_id={task_id} prediction_id={req.prediction_id}")
        return FeedbackSubmitResponse(
            feedback_id=task_id,
            prediction_id=req.prediction_id,
            status="submitted",
            message="Feedback ถูกส่งไปยัง Label Studio เรียบร้อยแล้ว รอ expert ตรวจสอบ",
        )

    except HTTPException:
        raise  # re-raise HTTPException จาก layer ล่าง

    except (ConnectionError, requests.exceptions.ConnectionError) as e:
        logger.warning(f"[submit] Label Studio unreachable: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ไม่สามารถเชื่อมต่อกับ Label Studio ได้ กรุณาลองใหม่ภายหลัง",
        )

    except Exception as e:
        logger.error(f"[submit] unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Label Studio ตอบกลับผิดพลาด: {str(e)[:200]}",
        )


def fetch_reviewed_feedback() -> list[ReviewedFeedbackItem]:
    """
    ดึง annotation ที่ expert ตรวจสอบแล้วจาก Label Studio

    Flow:
    1. เรียก core/label_studio_tasks.get_completed_annotations()
    2. แปลงผลลัพธ์เป็น ReviewedFeedbackItem list
    3. ถ้า Label Studio ไม่พร้อม → คืน HTTPException 503

    Returns:
        list ของ ReviewedFeedbackItem
    """
    logger.info(f"[reviewed] fetching completed annotations project_id={FEEDBACK_PROJECT_ID}")

    try:
        raw = get_completed_annotations(project_id=FEEDBACK_PROJECT_ID)
        items = [_parse_annotation(a) for a in raw]
        logger.info(f"[reviewed] found {len(items)} reviewed items")
        return items

    except HTTPException:
        raise

    except (ConnectionError, requests.exceptions.ConnectionError) as e:
        logger.warning(f"[reviewed] Label Studio unreachable: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="ไม่สามารถเชื่อมต่อกับ Label Studio ได้ กรุณาลองใหม่ภายหลัง",
        )

    except Exception as e:
        logger.error(f"[reviewed] unexpected error: {e}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Label Studio ตอบกลับผิดพลาด: {str(e)[:200]}",
        )


# ── Private helpers ──

def _extract_task_id(result: dict | list, fallback_prediction_id: str) -> str:
    """แปลง response จาก Label Studio เป็น task_id string"""
    if isinstance(result, list) and result:
        return f"task_{result[0].get('id', uuid.uuid4().hex[:8])}"
    if isinstance(result, dict):
        # Label Studio อาจคืน {"task_count": N} หรือ {"id": N}
        tid = result.get("id") or result.get("task_count")
        if tid:
            return f"task_{tid}"
    return f"task_fb_{fallback_prediction_id}"


def _parse_annotation(raw: dict) -> ReviewedFeedbackItem:
    """แปลง raw annotation dict จาก Label Studio เป็น ReviewedFeedbackItem"""
    data = raw.get("data", {})
    return ReviewedFeedbackItem(
        task_id=raw.get("id", 0),
        prediction_id=data.get("prediction_id"),
        input_text=data.get("text"),
        predicted_label=data.get("predicted_label"),
        correct_label=data.get("user_correction"),
        annotations=raw.get("annotations", []),
    )
