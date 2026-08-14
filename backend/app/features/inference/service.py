"""
inference/service.py — Business logic สำหรับ Inference feature

แยก logic การประมวลผลออกจาก router เพื่อให้ทดสอบและสลับ implementation ได้ง่าย

TODO: แทนที่ _mock_run_model() ด้วย logic จริง เช่น:
  - โหลดโมเดลจาก MLflow / HuggingFace Transformers
  - เรียก Triton Inference Server หรือ TorchServe
  - Call GPU worker ผ่าน Redis queue (arq)
"""

import time
import uuid
from typing import Optional

from fastapi import HTTPException

from app.features.inference.schemas import (
    PredictRequest,
    PredictResponse,
    PredictionHistoryItem,
)
from core.logger import setup_custom_logger

logger = setup_custom_logger("inference.service")

# ── In-memory history store (mock) ──
# TODO: แทนที่ด้วย PostgreSQL table เพื่อ persist ข้ามการ restart
_prediction_history: list[PredictionHistoryItem] = []
MAX_HISTORY = 100  # เก็บไว้สูงสุด 100 รายการต่อ process


def run_predict(req: PredictRequest) -> PredictResponse:
    """
    ประมวลผล input เดียวผ่านโมเดล AI (ปัจจุบันเป็น mock)

    Flow:
    1. ตรวจสอบ input ว่ามี input_text หรือ image_url อย่างใดอย่างหนึ่ง
    2. ส่งเข้า _mock_run_model() (จะถูกแทนด้วย logic จริงทีหลัง)
    3. บันทึกลง history และ log
    4. คืน PredictResponse

    Args:
        req: PredictRequest ที่มี input_text หรือ image_url

    Returns:
        PredictResponse พร้อม prediction_id, result, confidence, latency
    """
    if not req.input_text and not req.image_url:
        raise HTTPException(
            status_code=422,
            detail="ต้องระบุ input_text หรือ image_url อย่างใดอย่างหนึ่ง",
        )

    start = time.perf_counter()
    result, confidence, input_type = _mock_run_model(req)
    latency_ms = round((time.perf_counter() - start) * 1000, 3)

    prediction_id = f"pred_{uuid.uuid4().hex[:12]}"

    response = PredictResponse(
        prediction_id=prediction_id,
        result=result,
        confidence=confidence,
        model_version=req.model_version,
        latency_ms=latency_ms,
        input_type=input_type,
    )

    # เก็บลง in-memory history
    _store_history(response)

    logger.info(
        f"[predict] id={prediction_id} type={input_type} "
        f"confidence={confidence} latency={latency_ms}ms"
    )
    return response


def run_batch_predict(requests: list[PredictRequest]) -> list[PredictResponse]:
    """
    ประมวลผลหลาย input พร้อมกัน (sequential mock, parallel จริงใน production)

    Args:
        requests: รายการ PredictRequest

    Returns:
        รายการ PredictResponse ตามลำดับ
    """
    results = []
    for req in requests:
        results.append(run_predict(req))
    return results


def get_history(limit: int = 20) -> list[PredictionHistoryItem]:
    """
    ดึงประวัติ prediction ล่าสุด (เรียงจากใหม่ไปเก่า)

    Args:
        limit: จำนวนรายการที่ต้องการ (ค่าเริ่มต้น 20)

    Returns:
        รายการ PredictionHistoryItem
    """
    return list(reversed(_prediction_history))[:limit]


# ── Private helpers ──

def _mock_run_model(req: PredictRequest) -> tuple[str, float, str]:
    """
    [MOCK] จำลองการเรียกใช้งานโมเดล AI
    คืน (result, confidence, input_type)

    TODO: แทนที่ด้วย inference จริง
    """
    if req.input_text:
        text = req.input_text
        # Mock sentiment ง่ายๆ จากคำ
        positive_words = {"ชอบ", "ดี", "เยี่ยม", "สุดยอด", "รัก", "สนุก", "ดีมาก"}
        negative_words = {"ไม่ดี", "แย่", "เกลียด", "น่าเบื่อ", "ผิดหวัง"}
        words = set(text.split())
        if words & negative_words:
            sentiment, conf = "Negative", 0.88
        elif words & positive_words:
            sentiment, conf = "Positive", 0.92
        else:
            sentiment, conf = "Neutral", 0.75

        snippet = text[:40] + "..." if len(text) > 40 else text
        return f"[MOCK] Sentiment: {sentiment} — '{snippet}'", conf, "text"

    else:
        # Image mock
        return f"[MOCK] Detected: object (url={req.image_url})", 0.85, "image"


def _store_history(response: PredictResponse) -> None:
    """เก็บ prediction ลง in-memory store (กันล้น MAX_HISTORY)"""
    global _prediction_history
    item = PredictionHistoryItem(
        prediction_id=response.prediction_id,
        result=response.result,
        confidence=response.confidence,
        model_version=response.model_version,
        input_type=response.input_type,
        latency_ms=response.latency_ms,
    )
    _prediction_history.append(item)
    if len(_prediction_history) > MAX_HISTORY:
        _prediction_history = _prediction_history[-MAX_HISTORY:]
