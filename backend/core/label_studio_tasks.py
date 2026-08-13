"""
core/label_studio_tasks.py — Helper functions สำหรับจัดการ Task ใน Label Studio

ใช้ร่วมกับ label_studio_client.py
"""

from core.label_studio_client import get_label_studio_client
from core.logger import setup_custom_logger

logger = setup_custom_logger("label_studio_tasks")


def create_feedback_task(project_id: int, prediction_id: str, input_text: str, predicted_label: str, correct_label: str) -> dict:
    """
    สร้าง annotation task จาก feedback ของผู้ใช้
    ใช้เมื่อผู้ใช้บอกว่า prediction ผิด และต้องการให้ expert re-annotate
    """
    client = get_label_studio_client()
    task = {
        "data": {
            "prediction_id": prediction_id,
            "text": input_text,
            "predicted_label": predicted_label,
            "user_correction": correct_label,
        }
    }
    result = client.import_tasks(project_id, [task])
    logger.info(f"Created feedback task for prediction {prediction_id}")
    return result


def get_completed_annotations(project_id: int) -> list:
    """
    ดึง annotation ที่ expert ตรวจสอบเสร็จแล้ว
    ใช้สำหรับนำไป fine-tune โมเดล
    """
    client = get_label_studio_client()
    annotations = client.export_annotations(project_id)
    completed = [a for a in annotations if a.get("annotations")]
    logger.info(f"Found {len(completed)} completed annotations in project {project_id}")
    return completed
