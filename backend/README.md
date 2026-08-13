# Backend — AI Ecosystem

## แนวคิดหลัก: แยก `core/` ออกจาก `features/`

โครงสร้างนี้แบ่งโค้ดออกเป็น 2 ชั้นชัดเจน:

### `core/` — Infra Client Layer
คุยกับ external service โดยตรง (Postgres, MinIO, Label Studio)
ไม่มี business logic — เป็นแค่ "สะพาน" ไปหา infrastructure

| ไฟล์ | เชื่อมกับ |
|---|---|
| `config.py` | อ่านค่าจาก `.env` ผ่าน pydantic-settings |
| `database.py` | PostgreSQL ผ่าน SQLAlchemy |
| `logger.py` | Console + File logging |
| `minio_client.py` | MinIO Object Storage |
| `minio_setup.py` | สร้าง bucket ตอน startup |
| `label_studio_client.py` | Label Studio REST API |
| `label_studio_tasks.py` | Helper สำหรับ task management |

### `features/` — Business Logic Layer
แต่ละ feature รับผิดชอบ domain ของตัวเอง ไม่ยุ่งกับ infra โดยตรง

| Feature | Domain |
|---|---|
| `auth/` | Authentication, JWT, User management |
| `inference/` | AI Model prediction |
| `feedback/` | รับ feedback ส่งต่อ Label Studio |
| `mlops/` | Model management, Health check |
| `security/` | Token verification, Rate limit |

## ทำไมไม่ใช้ Layer-based (models/, routers/, services/ รวมกัน)?

| Layer-based | Feature-based |
|---|---|
| ทุก model รวมกันในโฟลเดอร์เดียว | แต่ละ feature มี model ของตัวเอง |
| เพิ่ม feature ต้องแตะหลายโฟลเดอร์ | เพิ่ม feature = เพิ่มโฟลเดอร์ใหม่ |
| ยากเมื่อโปรเจกต์ใหญ่ขึ้น | Scale ได้ง่าย |

## วิธีรัน

```bash
cd backend
uv run uvicorn main:app --reload
# เปิด http://localhost:8000/docs
```

## Export API list

```bash
uv run python scripts/export_api_list.py
# ได้ไฟล์ storage/artifacts/api_snapshot_YYYY-MM-DD.xlsx
```
