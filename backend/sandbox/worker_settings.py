import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from arq.connections import RedisSettings
from core.config import settings

async def simple_work(ctx, data: str):
    print("=== [Worker] Executing simple_work ===")
    print(f"Job Data: {data}")
    print("========================================")
    return f"Job successfully processed: {data}"

class WorkerSettings:
    functions = [simple_work]
    redis_settings = RedisSettings(host=settings.redis_host, port=settings.redis_port)
