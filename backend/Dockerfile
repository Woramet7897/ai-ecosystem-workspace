# ──────────────────────────────────────────────────────────────
# backend/Dockerfile — FastAPI API Server
#
# Build: docker build -t ai-ecosystem-backend .
# Run:   docker run -p 8000:8000 --env-file .env ai-ecosystem-backend
# ──────────────────────────────────────────────────────────────

FROM python:3.12-slim

# ── System packages ──
# git ใช้สำหรับ huggingface_hub snapshot_download บางกรณี
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl \
        git \
    && rm -rf /var/lib/apt/lists/*

# ── Install uv (fast Python package manager) ──
RUN pip install uv --no-cache-dir

# ── Working directory ──
WORKDIR /app

# ── Copy dependency files ก่อน (leverage Docker layer cache) ──
COPY pyproject.toml uv.lock ./

# ── Install dependencies (frozen = reproducible, no-dev = production) ──
# UV_PYTHON_DOWNLOADS=never บังคับให้ uv ใช้ Python ของ base image เท่านั้น
# ป้องกันการดาวน์โหลด Python เวอร์ชันอื่น (เช่น 3.14) ที่อาจไม่มี prebuilt wheel
ENV UV_PYTHON_DOWNLOADS=never
RUN uv sync --frozen --no-dev

# ── Copy source code ──
COPY . .

# ── Expose API port ──
EXPOSE 8000

# ── Healthcheck: FastAPI /docs ──
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/ || exit 1

# ── Start FastAPI ──
CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
