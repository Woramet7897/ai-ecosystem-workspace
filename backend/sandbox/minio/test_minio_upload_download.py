import sys
import os
from pathlib import Path
from minio import Minio
from minio.error import S3Error

# ใส่พาธของโปรเจกต์เพื่อให้ import จาก core ได้
sys.path.append(str(Path(__file__).parent.parent.parent))

from core.config import settings
from core.logger import setup_custom_logger

# ใช้งาน Custom Logger ที่สร้างขึ้น
logger = setup_custom_logger('MinIOTest')

def test_minio_upload_download():
    logger.info("=== เริ่มต้นทดสอบ MinIO Upload / Download ===")
    
    # ดึงค่าคอนฟิกจาก settings (.env)
    # ตัด http:// ออกเพื่อใช้กับไลบรารี Minio
    minio_endpoint = settings.minio_url.replace("http://", "").replace("https://", "")
    
    # 1. เริ่มต้น MinIO Client
    # Library ที่ใช้คือ 'minio' 
    client = Minio(
        minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False  # ใช้ http ธรรมดาในการทดสอบ
    )
    
    bucket_name = "user-profiles"
    
    try:
        # 2. ตรวจสอบว่ามี Bucket หรือยัง ถ้าไม่มีให้สร้างใหม่ (make_bucket)
        if not client.bucket_exists(bucket_name):
            client.make_bucket(bucket_name)
            logger.info(f"สร้าง Bucket '{bucket_name}' สำเร็จ")
        else:
            logger.info(f"พบ Bucket '{bucket_name}' อยู่แล้ว")

        # กำหนดไฟล์ต้นทางและชื่อ object ที่จะบันทึกใน MinIO
        source_file = str(Path(__file__).parent.parent.parent.parent / "profile.jpg")
        object_name = "profile.jpg"
        download_file = str(Path(__file__).parent / "downloaded_profile.jpg")

        if not os.path.exists(source_file):
            logger.error(f"ไม่พบไฟล์ต้นฉบับ: {source_file}")
            return

        # 3. ทดสอบ Upload ข้อมูล (fput_object)
        logger.info(f"กำลัง Upload รูปภาพ '{source_file}' ไปที่ '{object_name}'...")
        client.fput_object(bucket_name, object_name, source_file)
        logger.info(f"Upload ข้อมูล '{object_name}' สำเร็จ")

        # 4. ทดสอบ Download ข้อมูล (fget_object)
        logger.info(f"กำลัง Download รูปภาพ '{object_name}' มาที่ '{download_file}'...")
        client.fget_object(bucket_name, object_name, download_file)
        logger.info(f"Download ข้อมูลมาที่ '{download_file}' สำเร็จ")
        
        # ตรวจสอบว่าไฟล์ถูกดาวน์โหลดมาจริง
        if os.path.exists(download_file):
            logger.info(f"ทดสอบสำเร็จ! พบไฟล์ {download_file} ขนาด {os.path.getsize(download_file)} bytes")
            
    except S3Error as exc:
        logger.error(f"เกิดข้อผิดพลาดจาก S3: {exc}")
    except Exception as e:
        logger.error(f"เกิดข้อผิดพลาด: {e}")

if __name__ == "__main__":
    test_minio_upload_download()
