"""
mlops.py - MLOps API
ด้านที่ 3: Model Management, Health Check, System Status

ช่วยให้ทีมงานดูสถานะของระบบ AI ทั้งหมดในที่เดียว:
- โมเดลที่มีอยู่ทั้งหมดและเวอร์ชันที่ active
- สถานะของ Postgres, Worker Queue
- การใช้งาน GPU/VRAM (ถ้ามี)
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List
import time

from core.config import settings
from core.logger import setup_custom_logger
from features.security import verify_token

logger = setup_custom_logger("mlops")

router = APIRouter(
    prefix="/mlops",
    tags=["MLOps"],
)

# ──────────────────────────────────────────────
# [MOCK] In-memory Model Registry
# TODO: แทนที่ด้วย MLflow หรือ database จริง
# ──────────────────────────────────────────────
MODEL_REGISTRY = {
    "v1": {"name": "sentiment-model", "version": "v1", "active": False, "accuracy": 0.88, "created_at": "2024-01-01"},
    "v2": {"name": "sentiment-model", "version": "v2", "active": True,  "accuracy": 0.93, "created_at": "2024-06-15"},
    "v3": {"name": "sentiment-model", "version": "v3", "active": False, "accuracy": 0.95, "created_at": "2024-12-01"},
}
ACTIVE_MODEL_VERSION = "v2"


# ──────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────

class ModelInfo(BaseModel):
    """ข้อมูลของโมเดลแต่ละเวอร์ชัน"""
    version:    str   = Field(..., description="เวอร์ชันของโมเดล เช่น v1, v2")
    name:       str   = Field(..., description="ชื่อโมเดล")
    active:     bool  = Field(..., description="เป็นเวอร์ชันที่กำลัง serve อยู่หรือไม่")
    accuracy:   float = Field(..., description="ความแม่นยำบน validation set")
    created_at: str   = Field(..., description="วันที่สร้าง/ลงทะเบียนโมเดล")

class ModelListResponse(BaseModel):
    """Response สำหรับ list โมเดลทั้งหมด"""
    models:         List[ModelInfo] = Field(..., description="รายการโมเดลทั้งหมด")
    active_version: str             = Field(..., description="เวอร์ชันที่กำลัง active อยู่")
    total:          int             = Field(..., description="จำนวนโมเดลทั้งหมด")

class ActivateRequest(BaseModel):
    """Schema สำหรับสลับโมเดลที่ active"""
    version: str = Field(..., description="เวอร์ชันที่ต้องการเปิดใช้งาน เช่น 'v3'")

class ActivateResponse(BaseModel):
    """Response หลังสลับโมเดล"""
    previous_version: str = Field(..., description="เวอร์ชันก่อนหน้า")
    active_version:   str = Field(..., description="เวอร์ชันที่ active อยู่ตอนนี้")
    message:          str = Field(..., description="ข้อความยืนยัน")

class ServiceStatus(BaseModel):
    """สถานะของแต่ละ service"""
    name:    str  = Field(..., description="ชื่อ service")
    healthy: bool = Field(..., description="พร้อมใช้งานหรือไม่")
    detail:  str  = Field(..., description="รายละเอียดเพิ่มเติม")

class HealthResponse(BaseModel):
    """Response สำหรับ health check รวม"""
    status:   str                 = Field(..., description="สถานะรวม: healthy / degraded / unhealthy")
    services: List[ServiceStatus] = Field(..., description="สถานะของแต่ละ service")
    gpu_vram_mb: Optional[float]  = Field(None, description="VRAM ที่ว่างอยู่ (MB) ถ้ามี GPU")
    timestamp: str                = Field(..., description="เวลาที่ตรวจสอบ")


# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────

def _check_postgres() -> ServiceStatus:
    """
    [CONNECTED] ตรวจสอบ Postgres จริงผ่าน psycopg
    ใช้ config จาก settings (postgres_host, postgres_port, postgres_user, etc.)
    """
    try:
        import psycopg
        conn_str = (
            f"host={settings.postgres_host} "
            f"port={settings.postgres_port} "
            f"dbname={settings.postgres_db} "
            f"user={settings.postgres_user} "
            f"password={settings.postgres_password} "
            f"connect_timeout=3"
        )
        with psycopg.connect(conn_str) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        return ServiceStatus(name="PostgreSQL", healthy=True, detail="Connected successfully")
    except Exception as e:
        logger.warning(f"[health] Postgres ไม่พร้อมใช้งาน: {e}")
        return ServiceStatus(name="PostgreSQL", healthy=False, detail=str(e))


def _check_redis() -> ServiceStatus:
    """
    [CONNECTED] ตรวจสอบ Redis จริงผ่าน redis-py
    ใช้ config จาก settings (redis_host, redis_port)
    """
    try:
        import redis as redis_lib
        r = redis_lib.Redis(host=settings.redis_host, port=settings.redis_port, socket_connect_timeout=3)
        r.ping()
        return ServiceStatus(name="Redis (Worker Queue)", healthy=True, detail="PONG received")
    except Exception as e:
        logger.warning(f"[health] Redis ไม่พร้อมใช้งาน: {e}")
        return ServiceStatus(name="Redis (Worker Queue)", healthy=False, detail=str(e))


def _check_minio() -> ServiceStatus:
    """
    [CONNECTED] ตรวจสอบ MinIO จริงผ่าน minio library
    """
    try:
        from minio import Minio
        endpoint = settings.minio_url.replace("http://", "").replace("https://", "")
        client = Minio(endpoint, access_key=settings.minio_access_key, secret_key=settings.minio_secret_key, secure=False)
        # ลอง list buckets เพื่อตรวจสอบการเชื่อมต่อ
        list(client.list_buckets())
        return ServiceStatus(name="MinIO", healthy=True, detail="Connected successfully")
    except Exception as e:
        logger.warning(f"[health] MinIO ไม่พร้อมใช้งาน: {e}")
        return ServiceStatus(name="MinIO", healthy=False, detail=str(e))


def _check_gpu() -> Optional[float]:
    """
    [MOCK] เช็ค GPU VRAM
    TODO: ใช้ pynvml หรือ torch.cuda.memory_reserved() จริง
    """
    try:
        import torch
        if torch.cuda.is_available():
            free = torch.cuda.mem_get_info()[0] / 1024 / 1024  # convert to MB
            return round(free, 1)
    except ImportError:
        pass
    return None  # ไม่มี GPU หรือ torch ไม่ถูก install


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.get(
    "/models",
    response_model=ModelListResponse,
    summary="ดูโมเดลทั้งหมดที่มีในระบบ",
    description="แสดงรายการโมเดลทั้งหมดที่ลงทะเบียนไว้ พร้อมระบุว่าเวอร์ชันไหน active อยู่",
)
def list_models(token: str = Depends(verify_token)):
    """
    GET /mlops/models

    List โมเดลทั้งหมดใน model registry
    [MOCK] ข้อมูลมาจาก MODEL_REGISTRY dict ใน memory
    TODO: ต่อกับ MLflow Model Registry หรือ database จริง
    """
    logger.info("[list_models] ดึงรายการโมเดลทั้งหมด")
    models = [ModelInfo(**v) for v in MODEL_REGISTRY.values()]
    return ModelListResponse(
        models=models,
        active_version=ACTIVE_MODEL_VERSION,
        total=len(models),
    )


@router.post(
    "/models/activate",
    response_model=ActivateResponse,
    summary="สลับโมเดลที่ใช้งานอยู่",
    description="สลับเวอร์ชันโมเดลที่ใช้งาน (Blue-Green Deployment) โดยไม่ต้องรีสตาร์ทระบบ",
)
def activate_model(req: ActivateRequest, token: str = Depends(verify_token)):
    """
    POST /mlops/models/activate

    สลับโมเดลที่ active ไปเป็นเวอร์ชันที่กำหนด
    [MOCK] อัปเดต flag ใน MODEL_REGISTRY ใน memory
    TODO: ต่อกับ model server จริง (เช่น Triton config reload, MLflow transition)
    """
    global ACTIVE_MODEL_VERSION

    if req.version not in MODEL_REGISTRY:
        raise HTTPException(status_code=404, detail=f"ไม่พบโมเดลเวอร์ชัน '{req.version}' ใน registry")

    previous = ACTIVE_MODEL_VERSION
    # อัปเดต active flag
    for v in MODEL_REGISTRY.values():
        v["active"] = (v["version"] == req.version)
    ACTIVE_MODEL_VERSION = req.version

    logger.info(f"[activate_model] สลับจาก {previous} -> {req.version} [MOCK]")

    return ActivateResponse(
        previous_version=previous,
        active_version=ACTIVE_MODEL_VERSION,
        message=f"สลับ active model เป็น {req.version} เรียบร้อย [MOCK]",
    )


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="ตรวจสอบสถานะทุก Service ในระบบ",
    description="ตรวจสอบสถานะจริงของทุก service ในระบบ: Postgres, Redis, MinIO และ GPU (ถ้ามี)",
)
def health_check(token: str = Depends(verify_token)):
    """
    GET /mlops/health

    เช็คสถานะของทุก service พร้อมกัน
    - PostgreSQL: [CONNECTED] ใช้ psycopg ต่อจริง
    - Redis:      [CONNECTED] ใช้ redis-py ต่อจริง
    - MinIO:      [CONNECTED] ใช้ minio library ต่อจริง
    - GPU/VRAM:   [MOCK] ต้อง install torch ถึงจะได้ข้อมูลจริง
    """
    logger.info("[health] เริ่มต้น health check ทุก service")

    services = [
        _check_postgres(),
        _check_redis(),
        _check_minio(),
    ]

    gpu_vram = _check_gpu()

    all_healthy = all(s.healthy for s in services)
    any_healthy = any(s.healthy for s in services)
    status = "healthy" if all_healthy else ("degraded" if any_healthy else "unhealthy")

    logger.info(f"[health] ผลรวม status={status}")

    return HealthResponse(
        status=status,
        services=services,
        gpu_vram_mb=gpu_vram,
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    )
