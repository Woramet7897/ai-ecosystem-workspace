import sys
import os
from pathlib import Path
from minio import Minio
from minio.error import S3Error
from minio.versioningconfig import VersioningConfig, ENABLED

# ใส่พาธของโปรเจกต์เพื่อให้ import จาก core ได้
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.config import settings
from core.logger import setup_custom_logger

logger = setup_custom_logger('MinIOVersioning')

def test_minio_versioning():
    logger.info("=== เริ่มต้นทดสอบ MinIO Versioning ===")
    
    minio_endpoint = settings.minio_url.replace("http://", "").replace("https://", "")
    client = Minio(
        minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False
    )
    
    bucket_name = "user-profiles-versioned"
    
    try:
        # 1. สร้าง Bucket และเปิดใช้งาน Versioning (set_bucket_versioning)
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            logger.info(f"สร้าง Bucket '{bucket_name}' สำเร็จ")
            
        client.set_bucket_versioning(bucket_name, VersioningConfig(ENABLED))
        logger.info(f"เปิดใช้งาน Versioning สำหรับ Bucket '{bucket_name}' เรียบร้อยแล้ว")

        # เตรียมไฟล์ที่จะใช้ทดสอบ (profile.jpg และ profile2.jpg)
        source_file_v1 = str(Path(__file__).parent.parent.parent.parent / "profile.jpg")
        source_file_v2 = str(Path(__file__).parent.parent.parent.parent / "profile2.jpg")
        object_name = "my_photo.jpg"

        if not os.path.exists(source_file_v1) or not os.path.exists(source_file_v2):
            logger.error("ไม่พบไฟล์รูปภาพสำหรับการทดสอบ กรุณาเตรียม profile.jpg และ profile2.jpg ไว้ที่โฟลเดอร์นอกสุด")
            return

        # 2. Upload ไฟล์เวอร์ชั่นที่ 1
        logger.info(f"กำลัง Upload รูปภาพเวอร์ชั่น 1 ({source_file_v1})...")
        result_v1 = client.fput_object(bucket_name, object_name, source_file_v1)
        version_id_v1 = result_v1.version_id
        logger.info(f"Upload เวอร์ชั่น 1 สำเร็จ! ได้รับ Version ID: {version_id_v1}")

        # 3. Upload ไฟล์เวอร์ชั่นที่ 2 ทับชื่อเดิม (my_photo.jpg)
        logger.info(f"กำลัง Upload รูปภาพเวอร์ชั่น 2 ({source_file_v2}) ทับชื่อ object เดิม...")
        result_v2 = client.fput_object(bucket_name, object_name, source_file_v2)
        version_id_v2 = result_v2.version_id
        logger.info(f"Upload เวอร์ชั่น 2 สำเร็จ! ได้รับ Version ID: {version_id_v2}")

        # 4. ทดสอบโหลดข้อมูลแบบไม่ระบุ Version (ควรจะได้รูปเวอร์ชั่น 2 ล่าสุด)
        download_latest = str(Path(__file__).parent / "downloaded_latest.jpg")
        logger.info("กำลังทดสอบ Download แบบ 'ไม่ระบุ version'...")
        client.fget_object(bucket_name, object_name, download_latest)
        logger.info(f"Download เสร็จสิ้น: ได้รูปไฟล์ล่าสุดมาที่ '{download_latest}'")

        # 5. ทดสอบโหลดข้อมูลแบบระบุ Version (ดึงรูปเวอร์ชั่น 1 กลับมา)
        download_v1 = str(Path(__file__).parent / "downloaded_v1.jpg")
        logger.info(f"กำลังทดสอบ Download แบบ 'ระบุ version' โดยระบุ ID = {version_id_v1}...")
        client.fget_object(bucket_name, object_name, download_v1, version_id=version_id_v1)
        logger.info(f"Download เสร็จสิ้น: ได้รูปไฟล์เวอร์ชั่นแรกกลับมาที่ '{download_v1}'")

        logger.info("=== จบการทดสอบ MinIO Versioning ===")
            
    except S3Error as exc:
        logger.error(f"เกิดข้อผิดพลาดจาก S3: {exc}")
    except Exception as e:
        logger.error(f"เกิดข้อผิดพลาด: {e}")

if __name__ == "__main__":
    test_minio_versioning()
