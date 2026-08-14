"""
feedback/schemas.py — Pydantic request/response schemas สำหรับ Feedback API
"""

from typing import Any, List, Optional
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Request Schemas
# ──────────────────────────────────────────────

class FeedbackSubmitRequest(BaseModel):
    """Request body สำหรับ POST /feedback/submit"""

    prediction_id:   str = Field(
        ...,
        description="ID ของ prediction ที่ต้องการแจ้งว่าผิด (ได้จาก /inference/predict)",
    )
    input_text:      str = Field(
        ...,
        description="ข้อความต้นฉบับที่ใช้ predict",
        max_length=2000,
    )
    predicted_label: str = Field(
        ...,
        description="label ที่โมเดลทำนายออกมา (ค่าที่ผิด)",
    )
    correct_label:   str = Field(
        ...,
        description="label ที่ถูกต้องตามความเห็นของผู้ใช้",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "prediction_id": "pred_18b6a0e291d3",
                "input_text": "ผมชอบโปรเจกต์นี้มาก",
                "predicted_label": "Negative",
                "correct_label": "Positive",
            }
        }
    }


# ──────────────────────────────────────────────
# Response Schemas
# ──────────────────────────────────────────────

class FeedbackSubmitResponse(BaseModel):
    """Response จาก POST /feedback/submit"""

    feedback_id:   str = Field(..., description="ID ของ task ที่สร้างใน Label Studio")
    prediction_id: str = Field(..., description="ID ของ prediction ที่ถูกรายงาน")
    status:        str = Field(..., description="สถานะของ feedback: 'submitted' หรือ 'error'")
    message:       str = Field(..., description="ข้อความอธิบายผลลัพธ์")

    model_config = {
        "json_schema_extra": {
            "example": {
                "feedback_id":   "task_42",
                "prediction_id": "pred_18b6a0e291d3",
                "status":        "submitted",
                "message":       "Feedback ถูกส่งไปยัง Label Studio เรียบร้อยแล้ว",
            }
        }
    }


class ReviewedFeedbackItem(BaseModel):
    """ข้อมูล annotation 1 รายการที่ expert ตรวจสอบแล้ว"""

    task_id:         int            = Field(..., description="ID ของ task ใน Label Studio")
    prediction_id:   Optional[str]  = Field(None, description="ID ของ prediction ต้นฉบับ")
    input_text:      Optional[str]  = Field(None, description="ข้อความต้นฉบับที่ submit มา")
    predicted_label: Optional[str]  = Field(None, description="label ที่โมเดลทำนาย (ค่าที่ผิด)")
    correct_label:   Optional[str]  = Field(None, description="label ที่ผู้ใช้แก้ไข")
    annotations:     List[Any]      = Field(default_factory=list, description="annotation จาก expert ใน Label Studio")


class ReviewedFeedbackResponse(BaseModel):
    """Response จาก GET /feedback/reviewed"""

    items: List[ReviewedFeedbackItem] = Field(..., description="รายการ annotation ที่ expert ตรวจสอบแล้ว")
    total: int                        = Field(..., description="จำนวนรายการทั้งหมด")
