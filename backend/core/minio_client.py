"""
core/minio_client.py — MinIO client wrapper

ทำหน้าที่สร้าง Minio client จาก env vars และ expose helper functions
feature อื่นๆ import จากไฟล์นี้ ไม่ต้อง init client ซ้ำ
"""

from minio import Minio
from minio.error import S3Error
from core.config import settings
from core.logger import setup_custom_logger

logger = setup_custom_logger("minio_client")

# Singleton MinIO client
_client: Minio | None = None


def get_minio_client() -> Minio:
    """คืน MinIO client (สร้างครั้งเดียว ใช้ซ้ำ)"""
    global _client
    if _client is None:
        endpoint = settings.minio_url.replace("http://", "").replace("https://", "")
        _client = Minio(
            endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=False,
        )
    return _client


def get_presigned_url(bucket: str, object_name: str, expires_seconds: int = 3600) -> str:
    """
    สร้าง presigned URL สำหรับให้ client download ไฟล์โดยตรงจาก MinIO
    ไม่ต้องผ่าน backend — ลด load และเร็วกว่า
    """
    from datetime import timedelta
    client = get_minio_client()
    return client.presigned_get_object(
        bucket, object_name, expires=timedelta(seconds=expires_seconds)
    )


def upload_bytes(bucket: str, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    """
    Upload ข้อมูล bytes ขึ้น MinIO
    คืน object_name ที่บันทึกสำเร็จ
    """
    import io
    client = get_minio_client()
    client.put_object(
        bucket, object_name,
        data=io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    logger.info(f"Uploaded {object_name} to bucket '{bucket}'")
    return object_name


def ensure_bucket(bucket: str) -> None:
    """สร้าง bucket ถ้ายังไม่มี (idempotent)"""
    client = get_minio_client()
    if not client.bucket_exists(bucket):
        client.make_bucket(bucket)
        logger.info(f"Created bucket: '{bucket}'")


def upload_file(bucket: str, object_name: str, file_path: str, content_type: str = "application/octet-stream") -> str:
    """
    Upload ไฟล์จาก local path ขึ้น MinIO
    คืน object_name ที่บันทึกสำเร็จ
    """
    client = get_minio_client()
    ensure_bucket(bucket)
    client.fput_object(bucket, object_name, file_path, content_type=content_type)
    logger.info(f"Uploaded file {file_path} -> bucket '{bucket}/{object_name}'")
    return object_name


def download_file(bucket: str, object_name: str, dest_path: str) -> str:
    """
    Download ไฟล์จาก MinIO ลง local path
    คืน dest_path ที่ดาวน์โหลดสำเร็จ
    """
    client = get_minio_client()
    client.fget_object(bucket, object_name, dest_path)
    logger.info(f"Downloaded bucket '{bucket}/{object_name}' -> {dest_path}")
    return dest_path


def list_objects(bucket: str, prefix: str = "") -> list[str]:
    """
    List รายชื่อ object ใน bucket ที่ขึ้นต้นด้วย prefix
    คืน list ของ object_name
    """
    client = get_minio_client()
    objects = client.list_objects(bucket, prefix=prefix, recursive=True)
    names = [obj.object_name for obj in objects]
    logger.info(f"Listed {len(names)} objects in bucket '{bucket}' prefix='{prefix}'")
    return names

