"""
inference/schemas.py — Pydantic request/response schemas สำหรับ Inference API

แยกออกมาเพื่อให้ router.py และ service.py import ร่วมกันได้ง่าย
และสะดวกเมื่อต้องการ generate OpenAPI documentation
"""

from typing import Optional, List
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Request Schemas
# ──────────────────────────────────────────────

class PredictRequest(BaseModel):
    """Request body สำหรับ POST /inference/predict"""

    input_text: Optional[str] = Field(
        None,
        description="ข้อความสำหรับงาน NLP เช่น sentiment analysis, classification",
        max_length=2000,
    )
    image_url: Optional[str] = Field(
        None,
        description="URL รูปภาพสำหรับงาน Computer Vision เช่น object detection",
    )
    model_version: str = Field(
        "v1",
        description="เวอร์ชันของโมเดลที่ต้องการใช้งาน",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "input_text": "ผมชอบโปรเจกต์นี้มาก",
                "model_version": "v1",
            }
        }
    }


class BatchPredictRequest(BaseModel):
    """Request body สำหรับ POST /inference/predict/batch"""

    items: List[PredictRequest] = Field(
        ...,
        description="รายการ input หลายรายการที่ต้องการประมวลผลพร้อมกัน",
        min_length=1,
        max_length=50,
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "items": [
                    {"input_text": "ข้อความที่ 1", "model_version": "v1"},
                    {"input_text": "ข้อความที่ 2", "model_version": "v1"},
                ]
            }
        }
    }


# ──────────────────────────────────────────────
# Response Schemas
# ──────────────────────────────────────────────

class PredictResponse(BaseModel):
    """Response จาก POST /inference/predict"""

    prediction_id:  str   = Field(..., description="ID เฉพาะของการ predict ครั้งนี้ ใช้อ้างอิงใน /feedback ภายหลัง")
    result:         str   = Field(..., description="ผลลัพธ์จากโมเดล เช่น label หรือข้อความตอบกลับ")
    confidence:     float = Field(..., description="ความมั่นใจของโมเดล (0.0 – 1.0)", ge=0.0, le=1.0)
    model_version:  str   = Field(..., description="เวอร์ชันโมเดลที่ประมวลผลจริง")
    latency_ms:     float = Field(..., description="เวลาประมวลผล (milliseconds)")
    input_type:     str   = Field(..., description="ประเภท input ที่ใช้: 'text' หรือ 'image'")

    model_config = {
        "json_schema_extra": {
            "example": {
                "prediction_id": "pred_1723612345678",
                "result": "[MOCK] Sentiment: Positive (input: 'ผมชอบโปรเจกต์นี้มาก')",
                "confidence": 0.92,
                "model_version": "v1",
                "latency_ms": 12.5,
                "input_type": "text",
            }
        }
    }


class BatchPredictResponse(BaseModel):
    """Response จาก POST /inference/predict/batch"""

    results:          List[PredictResponse] = Field(..., description="ผลลัพธ์ของแต่ละ item ตามลำดับ")
    total:            int                   = Field(..., description="จำนวน item ทั้งหมดที่ประมวลผล")
    total_latency_ms: float                 = Field(..., description="เวลาประมวลผลรวมทั้งหมด (milliseconds)")


class PredictionHistoryItem(BaseModel):
    """ข้อมูล prediction 1 รายการในประวัติ"""

    prediction_id: str
    user_id:       str   # UUID ของ user เจ้าของ prediction (ใช้ filter ใน get_history)
    result:        str
    confidence:    float
    model_version: str
    input_type:    str
    latency_ms:    float


class PredictionHistoryResponse(BaseModel):
    """Response จาก GET /inference/history"""

    items: List[PredictionHistoryItem] = Field(..., description="รายการประวัติ prediction ล่าสุด")
    total: int                         = Field(..., description="จำนวนรายการทั้งหมดในประวัติ")
