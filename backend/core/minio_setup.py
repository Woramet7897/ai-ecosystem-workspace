"""
core/minio_setup.py — ตั้งค่า MinIO ตอน startup

สร้าง bucket ที่จำเป็นถ้ายังไม่มี เรียกใน lifespan ของ FastAPI app
"""

from core.minio_client import get_minio_client
from core.logger import setup_custom_logger

logger = setup_custom_logger("minio_setup")

# รายชื่อ bucket ที่ระบบต้องใช้
REQUIRED_BUCKETS = [
    "user-profiles",          # รูปโปรไฟล์ผู้ใช้
    "user-profiles-versioned", # รูปโปรไฟล์แบบมี versioning
    "feedback-data",           # ข้อมูล feedback จาก prediction
    "model-artifacts",         # ไฟล์โมเดล (legacy)
    "datasets",                # training datasets (.parquet files)
    "models",                  # trained model artifacts + logs (versioned)
]



def ensure_buckets_exist() -> None:
    """
    ตรวจสอบและสร้าง bucket ที่จำเป็นทั้งหมด
    เรียกใน startup event ของ FastAPI
    """
    client = get_minio_client()
    for bucket in REQUIRED_BUCKETS:
        try:
            if not client.bucket_exists(bucket):
                client.make_bucket(bucket)
                logger.info(f"Created bucket: '{bucket}'")
            else:
                logger.info(f"Bucket already exists: '{bucket}'")
        except Exception as e:
            logger.error(f"Failed to create bucket '{bucket}': {e}")
