import asyncio
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from arq import create_pool
from arq.connections import RedisSettings
from core.config import settings

async def main():
    redis_settings = RedisSettings(host=settings.redis_host, port=settings.redis_port)
    redis = await create_pool(redis_settings)
    
    print("=== [Client] Enqueuing job 'simple_work' ===")
    print("Sending Data: Hello from AI-EcoSystem Sandbox!")
    
    await redis.enqueue_job('simple_work', 'Hello from AI-EcoSystem Sandbox!')
    
    print("Job enqueued successfully!")
    print("============================================")

if __name__ == '__main__':
    asyncio.run(main())
