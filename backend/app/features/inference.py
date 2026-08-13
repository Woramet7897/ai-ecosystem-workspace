"""
inference.py - Inference API
ด้านที่ 1: AI Model Prediction
รับข้อมูล input จาก client แล้วส่งผ่านโมเดล AI เพื่อประมวลผลและส่งผลลัพธ์กลับ
รองรับทั้ง NLP (input_text) และ Computer Vision (image_url)
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional, List
import time

from core.logger import setup_custom_logger
from app.features.security import verify_token

logger = setup_custom_logger("inference")

router = APIRouter(
    prefix="/inference",
    tags=["Inference"],
)

# ──────────────────────────────────────────────
# Pydantic Models (Request / Response Schemas)
# ──────────────────────────────────────────────

class PredictRequest(BaseModel):
    """Schema สำหรับส่ง request เข้า endpoint /predict"""
    input_text: Optional[str] = Field(None, description="ข้อความสำหรับงาน NLP เช่น sentiment analysis, classification")
    image_url:  Optional[str] = Field(None, description="URL รูปภาพสำหรับงาน Computer Vision เช่น object detection")
    model_version: str = Field("v1", description="เวอร์ชันของโมเดลที่ต้องการใช้งาน")

    class Config:
        json_schema_extra = {
            "example": {
                "input_text": "ผมชอบโปรเจกต์นี้มาก",
                "model_version": "v1"
            }
        }

class PredictResponse(BaseModel):
    """Schema สำหรับ response จาก endpoint /predict"""
    prediction_id: str  = Field(..., description="ID เฉพาะของการ predict ครั้งนี้ ใช้อ้างอิงใน feedback ภายหลัง")
    result:        str  = Field(..., description="ผลลัพธ์จากโมเดล")
    confidence:    float= Field(..., description="ความมั่นใจของโมเดล (0.0 - 1.0)")
    model_version: str  = Field(..., description="เวอร์ชันโมเดลที่ใช้งานจริง")
    latency_ms:    float= Field(..., description="เวลาประมวลผล (milliseconds)")

class BatchPredictRequest(BaseModel):
    """Schema สำหรับส่ง request เข้า endpoint /predict/batch"""
    items: List[PredictRequest] = Field(..., description="รายการ request หลายรายการที่ต้องการประมวลผลพร้อมกัน")

class BatchPredictResponse(BaseModel):
    """Schema สำหรับ response จาก endpoint /predict/batch"""
    results:    List[PredictResponse] = Field(..., description="ผลลัพธ์ของแต่ละรายการ")
    total:      int                   = Field(..., description="จำนวนรายการทั้งหมด")
    total_latency_ms: float           = Field(..., description="เวลารวมทั้งหมด (milliseconds)")


# ──────────────────────────────────────────────
# Helper Function (Mock)
# ──────────────────────────────────────────────

def _run_model(req: PredictRequest) -> PredictResponse:
    """
    [MOCK] จำลองการเรียกใช้งานโมเดล AI
    TODO: แทนที่ด้วย logic จริง เช่น
          - โหลดโมเดลจาก MLflow / HuggingFace
          - เรียก inference server (Triton, TorchServe)
          - หรือ call API ไปยัง GPU worker
    """
    start = time.perf_counter()

    # ── MOCK LOGIC ──
    if req.input_text:
        result = f"[MOCK] Sentiment: Positive (input: '{req.input_text[:30]}...')" if len(req.input_text) > 30 else f"[MOCK] Sentiment: Positive (input: '{req.input_text}')"
        confidence = 0.92
    elif req.image_url:
        result = f"[MOCK] Detected: cat (url: {req.image_url})"
        confidence = 0.85
    else:
        raise HTTPException(status_code=422, detail="ต้องระบุ input_text หรือ image_url อย่างใดอย่างหนึ่ง")
    # ── END MOCK ──

    latency = (time.perf_counter() - start) * 1000
    prediction_id = f"pred_{int(time.time() * 1000)}"

    return PredictResponse(
        prediction_id=prediction_id,
        result=result,
        confidence=confidence,
        model_version=req.model_version,
        latency_ms=round(latency, 3),
    )


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="ประมวลผล AI รายการเดียว",
    description="ส่ง input เดี่ยวเข้าโมเดล AI แล้วรับผลลัพธ์กลับ รองรับ NLP (input_text) และ Vision (image_url)",
)
def predict(req: PredictRequest, token: str = Depends(verify_token)):
    """
    POST /inference/predict

    รับ input จาก client (ข้อความหรือ URL รูปภาพ) แล้วส่งผ่านโมเดล AI ที่กำหนดเวอร์ชัน
    คืนผลลัพธ์พร้อม confidence score และ latency
    ใช้ prediction_id ที่ได้รับไปอ้างอิงใน /feedback/feedback ภายหลัง
    """
    logger.info(f"[predict] model_version={req.model_version} input_type={'text' if req.input_text else 'image'}")
    response = _run_model(req)
    logger.info(f"[predict] prediction_id={response.prediction_id} confidence={response.confidence}")
    return response


@router.post(
    "/predict/batch",
    response_model=BatchPredictResponse,
    summary="ประมวลผล AI หลายรายการพร้อมกัน",
    description="ส่ง input หลายรายการพร้อมกัน แล้วรับผลลัพธ์ทั้งหมดกลับในครั้งเดียว",
)
def predict_batch(req: BatchPredictRequest, token: str = Depends(verify_token)):
    """
    POST /inference/predict/batch

    ประมวลผลหลายรายการพร้อมกันในครั้งเดียว เหมาะสำหรับ bulk processing
    แต่ละ item ใน request จะถูกประมวลผลแยกกัน และส่ง response กลับในรูปแบบ list
    """
    logger.info(f"[predict_batch] จำนวน item = {len(req.items)}")
    start = time.perf_counter()

    results = []
    for item in req.items:
        results.append(_run_model(item))

    total_latency = (time.perf_counter() - start) * 1000
    logger.info(f"[predict_batch] เสร็จสิ้น total_latency={total_latency:.1f}ms")

    return BatchPredictResponse(
        results=results,
        total=len(results),
        total_latency_ms=round(total_latency, 3),
    )
