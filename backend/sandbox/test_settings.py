import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from core.config import settings

def test_settings_values():
    print(" Testing Settings from .env=")
    print(f"{'REDIS HOST':<20}: {settings.redis_host}")
    print(f"{'REDIS PORT':<20}: {settings.redis_port}")
    print(f"{'POSTGRES USER':<20}: {settings.postgres_user}")
    print(f"{'POSTGRES PASSWORD':<20}: {settings.postgres_password}")
    print(f"{'POSTGRES DB':<20}: {settings.postgres_db}")
    print(f"{'POSTGRES HOST':<20}: {settings.postgres_host}")
    print(f"{'POSTGRES PORT':<20}: {settings.postgres_port}")
    print(f"{'LABEL STUDIO URL':<20}: {settings.label_studio_url}")
    print(f"{'LABEL STUDIO API KEY':<20}: {settings.label_studio_api_key}")

if __name__ == "__main__":
    test_settings_values()