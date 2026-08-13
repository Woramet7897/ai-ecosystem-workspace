# AI Ecosystem Workspace

ระบบ Backend สำหรับ AI Ecosystem ที่ประกอบด้วย Inference, Feedback, MLOps, Security และ Authentication

## โครงสร้างระบบ

```
compose.yml          → รวม services: Postgres, MinIO, Label Studio, Redis
backend/             → FastAPI backend application
diagram/             → แผนภาพสถาปัตยกรรมระบบ
```

## Component และการเชื่อมต่อ

| Component | Port | คุยกับ |
|---|---|---|
| FastAPI Backend | 8000 | Postgres, MinIO, Label Studio, Redis |
| PostgreSQL | 5432 | เก็บข้อมูล user, model registry |
| MinIO | 9000/9001 | เก็บไฟล์ รูปภาพ feedback data |
| Label Studio | 8080 | รับ feedback task ส่ง annotation กลับ |
| Redis | 6379 | Background job queue |

## วิธีรัน

```bash
# 1. รัน infrastructure
docker compose up -d

# 2. รัน backend
cd backend
uv run uvicorn main:app --reload

# 3. เปิด Swagger UI
http://localhost:8000/docs
```

## GitHub

https://github.com/Woramet7897/ai-ecosystem-workspace