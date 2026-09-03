"""
core/redis_client.py - ARQ Redis Settings centralizer

แหล่งรวม RedisSettings เดียวของระบบ
ทุก module ที่ต้องการ ARQ pool ให้ import get_arq_redis_settings() จากที่นี่
แทนที่จะสร้าง RedisSettings(...) กระจายเองในหลายไฟล์
"""

from arq.connections import RedisSettings
from core.config import settings


def get_arq_redis_settings() -> RedisSettings:
    """
    คืน RedisSettings สำหรับ ARQ โดยอ่านค่าจาก core.config

    หมายเหตุเรื่อง port:
    - Local dev  : REDIS_HOST=localhost, REDIS_PORT=6381  (expose ออก host)
    - Docker network : REDIS_HOST=redis,    REDIS_PORT=6379  (internal container port)
    ค่าจะถูก override อัตโนมัติผ่าน environment variable ใน compose.yml
    """
    return RedisSettings(
        host=settings.redis_host,
        port=settings.redis_port,
    )
