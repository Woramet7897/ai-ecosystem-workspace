import logging
import os
import sys

def setup_custom_logger(name):
    """
    สร้างและคอนฟิก Custom Logger ของโปรเจกต์
    รองรับการเก็บ Log ลงไฟล์และแสดงบน Console
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # ป้องกันไม่ให้มีการเพิ่ม Handler ซ้ำ
    if not logger.handlers:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

        # 1. แสดงผลออกทางหน้าจอ (Console)
        # แก้ปัญหา UnicodeEncodeError บน Windows โดยการใช้เปิด Stream แบบรองรับ UTF-8
        console_handler = logging.StreamHandler(open(sys.stdout.fileno(), mode='w', encoding='utf-8', buffering=1) if sys.platform == 'win32' else sys.stdout)
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 2. บันทึกลงไฟล์ (File)
        # ตรวจสอบว่ามีโฟลเดอร์ logs หรือยัง
        log_dir = os.path.join(os.path.dirname(__file__), '..', 'logs')
        os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(os.path.join(log_dir, 'app.log'), encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger

# ทดสอบใช้งานเบื้องต้น
if __name__ == '__main__':
    log = setup_custom_logger('TestLogger')
    log.debug("This is a debug message")
    log.info("This is an info message")
    log.warning("This is a warning message")
    log.error("This is an error message")
