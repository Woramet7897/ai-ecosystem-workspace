"""
training/schemas.py - Pydantic schemas for Training Queue API
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


class TrainQueueRequest(BaseModel):
    """Request body สำหรับ POST /training/queue"""

    dataset_name: str = Field(
        ...,
        description="ชื่อ dataset ใน MinIO bucket 'datasets/' เช่น 'conll2003'",
        examples=["conll2003"],
    )
    model_name: str = Field(
        ...,
        description="ชื่อโมเดลที่จะสร้างใน MinIO bucket 'models/' เช่น 'ner-v1'",
        examples=["ner-v1"],
    )
    base_model: str = Field(
        default="bert-base-cased",
        description="HuggingFace model ID ที่ใช้เป็น base สำหรับ fine-tune",
    )
    start_time: datetime = Field(
        ...,
        description="เวลาที่ต้องการให้ worker เริ่มทำงาน (ISO 8601) — job จะอยู่สถานะ deferred จนถึงเวลานี้",
        examples=["2026-09-03T18:10:00+07:00"],
    )
    num_epochs: int = Field(default=3, ge=1, le=20, description="จำนวน epoch สำหรับ training")
    batch_size: int = Field(default=8, ge=1, le=64, description="Batch size ต่อ step")
    max_steps: int = Field(
        default=-1,
        description="จำกัดจำนวน step (-1 = ไม่จำกัด, ใช้ num_epochs แทน) — เหมาะสำหรับทดสอบ",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "dataset_name": "conll2003",
                "model_name": "ner-v1",
                "base_model": "bert-base-cased",
                "start_time": "2026-09-03T18:10:00+07:00",
                "num_epochs": 1,
                "batch_size": 8,
                "max_steps": 50,
            }
        }
    }


class TrainQueueResponse(BaseModel):
    """Response จาก POST /training/queue"""

    job_id:      str      = Field(..., description="ARQ Job ID สำหรับเช็คสถานะ")
    model_name:  str      = Field(..., description="ชื่อโมเดลที่จะถูกสร้าง")
    dataset_name: str     = Field(..., description="ชื่อ dataset ที่ใช้เทรน")
    status:      str      = Field(..., description="'deferred' หรือ 'queued'")
    start_time:  datetime = Field(..., description="เวลาที่ worker จะเริ่มทำงาน")
    message:     str      = Field(..., description="ข้อความอธิบาย")


class TrainStatusResponse(BaseModel):
    """Response จาก GET /training/queue/{job_id}"""

    job_id:      str           = Field(..., description="ARQ Job ID")
    status:      str           = Field(..., description="deferred / queued / in_progress / complete / not_found / failed")
    result:      Optional[Any] = Field(None, description="ผลลัพธ์ของ job เมื่อ complete")
    enqueue_time: Optional[str] = Field(None, description="เวลาที่ enqueue")
    start_time:  Optional[str] = Field(None, description="เวลาที่ worker เริ่มทำงาน")
    finish_time: Optional[str] = Field(None, description="เวลาที่ job เสร็จ")
