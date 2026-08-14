"""
inference/router.py — APIRouter สำหรับ Inference API endpoints

Endpoints:
  POST /inference/predict         — ประมวลผล AI รายการเดียว (ต้อง login)
  POST /inference/predict/batch   — ประมวลผล AI หลายรายการพร้อมกัน (ต้อง login)
  GET  /inference/history         — ดูประวัติ prediction ของ session นี้ (ต้อง login)
"""

import time
from fastapi import APIRouter, Depends, Query

from core.logger import setup_custom_logger
from app.features.auth.dependencies import get_current_active_user
from app.features.auth.models import User
from app.features.inference.schemas import (
    BatchPredictRequest,
    BatchPredictResponse,
    PredictRequest,
    PredictResponse,
    PredictionHistoryResponse,
)
from app.features.inference import service

logger = setup_custom_logger("inference.router")

router = APIRouter(
    prefix="/inference",
    tags=["Inference"],
)


# ──────────────────────────────────────────────
# POST /inference/predict
# ──────────────────────────────────────────────

@router.post(
    "/predict",
    response_model=PredictResponse,
    status_code=200,
    summary="ประมวลผล AI รายการเดียว",
    description="""
ส่ง input เดี่ยว (ข้อความหรือ URL รูปภาพ) เข้าโมเดล AI แล้วรับผลลัพธ์กลับ

**ต้องการ:** Bearer token จาก `/auth/login`

**Input:**
- `input_text` — ข้อความสำหรับงาน NLP (sentiment, classification)
- `image_url`  — URL รูปภาพสำหรับงาน Computer Vision
- ต้องมีอย่างน้อยหนึ่งอย่าง

**Output:**
- `prediction_id` — ใช้อ้างอิงใน `/feedback` ภายหลัง
- `result`        — ผลลัพธ์จากโมเดล
- `confidence`    — ความมั่นใจ 0.0–1.0
- `latency_ms`    — เวลาประมวลผล

> ⚠️ ปัจจุบันเป็น **mock** — ผลลัพธ์ถูกสุ่มตาม keyword ใน input
    """,
    response_description="ผลลัพธ์จากโมเดล AI พร้อม prediction_id และ confidence score",
)
def predict(
    req: PredictRequest,
    current_user: User = Depends(get_current_active_user),
):
    logger.info(
        f"[predict] user={current_user.email} "
        f"model={req.model_version} type={'text' if req.input_text else 'image'}"
    )
    return service.run_predict(req, user_id=str(current_user.id))


# ──────────────────────────────────────────────
# POST /inference/predict/batch
# ──────────────────────────────────────────────

@router.post(
    "/predict/batch",
    response_model=BatchPredictResponse,
    status_code=200,
    summary="ประมวลผล AI หลายรายการพร้อมกัน",
    description="""
ส่ง input หลายรายการพร้อมกันในครั้งเดียว เหมาะสำหรับ bulk processing
แต่ละ item ถูกประมวลผลแยกกัน ผลลัพธ์กลับมาในรูป list ตามลำดับ

**ต้องการ:** Bearer token จาก `/auth/login`

**ข้อจำกัด:** สูงสุด 50 items ต่อ request

> ⚠️ ปัจจุบันเป็น **mock** และประมวลผลแบบ sequential
    """,
    response_description="รายการผลลัพธ์ทั้งหมด พร้อมเวลารวม",
)
def predict_batch(
    req: BatchPredictRequest,
    current_user: User = Depends(get_current_active_user),
):
    logger.info(f"[predict_batch] user={current_user.email} items={len(req.items)}")
    start = time.perf_counter()

    results = service.run_batch_predict(req.items, user_id=str(current_user.id))
    total_latency = round((time.perf_counter() - start) * 1000, 3)

    logger.info(f"[predict_batch] done items={len(results)} total_latency={total_latency}ms")

    return BatchPredictResponse(
        results=results,
        total=len(results),
        total_latency_ms=total_latency,
    )


# ──────────────────────────────────────────────
# GET /inference/history
# ──────────────────────────────────────────────

@router.get(
    "/history",
    response_model=PredictionHistoryResponse,
    status_code=200,
    summary="ดูประวัติการ predict",
    description="""
ดึงประวัติ prediction ล่าสุดของ session นี้ เรียงจากใหม่ไปเก่า

**ต้องการ:** Bearer token จาก `/auth/login`

**หมายเหตุ:** ปัจจุบันเก็บใน in-memory store (หายเมื่อ restart server)
ในระบบจริงควรเก็บลง PostgreSQL table `prediction_logs`
    """,
    response_description="รายการประวัติ prediction ล่าสุด",
)
def get_history(
    limit: int = Query(20, ge=1, le=100, description="จำนวนรายการที่ต้องการ (1–100)"),
    current_user: User = Depends(get_current_active_user),
):
    logger.info(f"[history] user={current_user.email} limit={limit}")
    items = service.get_history(user_id=str(current_user.id), limit=limit)
    return PredictionHistoryResponse(items=items, total=len(items))
