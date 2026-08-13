"""
core/label_studio_client.py — Label Studio API client wrapper

ทำหน้าที่เชื่อมต่อ Label Studio ผ่าน REST API
feature อื่นๆ import จากไฟล์นี้แทนการ call API โดยตรง
"""

import requests
from core.config import settings
from core.logger import setup_custom_logger

logger = setup_custom_logger("label_studio_client")


class LabelStudioClient:
    """Wrapper สำหรับ Label Studio REST API"""

    def __init__(self):
        self.base_url = settings.label_studio_url.rstrip("/")
        self.headers = {
            "Authorization": f"Token {settings.label_studio_api_key}",
            "Content-Type": "application/json",
        }

    def _get(self, path: str) -> dict:
        """HTTP GET ไปยัง Label Studio"""
        resp = requests.get(f"{self.base_url}{path}", headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, data: dict) -> dict:
        """HTTP POST ไปยัง Label Studio"""
        resp = requests.post(f"{self.base_url}{path}", json=data, headers=self.headers, timeout=10)
        resp.raise_for_status()
        return resp.json()

    def health_check(self) -> bool:
        """ตรวจสอบว่า Label Studio พร้อมใช้งานหรือไม่"""
        try:
            self._get("/api/health")
            return True
        except Exception as e:
            logger.warning(f"Label Studio health check failed: {e}")
            return False

    def list_projects(self) -> list:
        """ดึงรายการโปรเจกต์ทั้งหมดใน Label Studio"""
        data = self._get("/api/projects")
        return data.get("results", [])

    def create_project(self, title: str, label_config: str) -> dict:
        """สร้างโปรเจกต์ใหม่ใน Label Studio"""
        result = self._post("/api/projects", {"title": title, "label_config": label_config})
        logger.info(f"Created Label Studio project: {title} (id={result.get('id')})")
        return result

    def import_tasks(self, project_id: int, tasks: list[dict]) -> dict:
        """นำเข้า task (ข้อมูลให้ annotate) เข้า project"""
        result = self._post(f"/api/projects/{project_id}/import", tasks)
        logger.info(f"Imported {len(tasks)} tasks to project {project_id}")
        return result

    def export_annotations(self, project_id: int, export_type: str = "JSON") -> list:
        """Export annotation ที่ annotate แล้วออกมาเป็น list"""
        data = self._get(f"/api/projects/{project_id}/export?exportType={export_type}")
        return data


# Singleton
_ls_client: LabelStudioClient | None = None


def get_label_studio_client() -> LabelStudioClient:
    """คืน LabelStudioClient (สร้างครั้งเดียว ใช้ซ้ำ)"""
    global _ls_client
    if _ls_client is None:
        _ls_client = LabelStudioClient()
    return _ls_client
