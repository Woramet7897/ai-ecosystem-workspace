# AI Ecosystem Backend

Backend หลักสำหรับระบบ AI Ecosystem พัฒนาด้วย **FastAPI** โดยใช้โครงสร้างแบบ **Feature-Based Architecture** เพื่อให้ระบบมีความเป็นระเบียบ สเกลได้ง่าย และดูแลรักษาสะดวก

## Tech Stack
* **Framework:** FastAPI
* **Database:** PostgreSQL (ผ่าน SQLAlchemy ORM)
* **Object Storage:** MinIO (สำหรับเก็บไฟล์, รูปภาพ, โมเดล)
* **Data Labeling:** Label Studio (ส่ง Feedback ไปสร้าง Annotation Task)
* **Authentication:** JWT (JSON Web Tokens)
* **Package Manager:** `uv`

## โครงสร้างโฟลเดอร์หลัก (Directory Structure)
```
backend/
├── app/
│   └── features/     # Business Logic ทั้งหมด แบ่งเป็นโมดูลตามฟีเจอร์ (เช่น auth, inference)
├── core/             # Infrastructure Layer เชื่อมต่อ Services ภายนอก (ไม่มี Business Logic)
├── scripts/          # สคริปต์ใช้งานทั่วไป (เช่น export_api_list)
├── main.py           # Entry point ของ FastAPI
└── pyproject.toml    # ไฟล์จัดการ dependencies ของระบบ
```

## วิธีการรันระบบ (How to Run)
1. ติดตั้ง dependencies ด้วย `uv`:
   ```bash
   uv sync
   ```
2. รัน FastAPI server:
   ```bash
   uv run uvicorn main:app --reload
   ```

## API Documentation
เมื่อรันเซิร์ฟเวอร์แล้ว สามารถดู API Docs และทดสอบยิง API ได้ที่:
* **Swagger UI:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **ReDoc:** [http://localhost:8000/redoc](http://localhost:8000/redoc)
* **OpenAPI JSON:** [http://localhost:8000/openapi.json](http://localhost:8000/openapi.json)

## สรุปรายการ Endpoints
ระบบนี้ประกอบด้วย Endpoints หลักที่แบ่งตามฟีเจอร์ ดังนี้:

| กลุ่ม (Tags) | Method | Endpoint | หน้าที่การทำงาน |
| --- | --- | --- | --- |
| **Root** | `GET` | `/` | Health check เบื้องต้น ตรวจสอบว่า API ทำงานอยู่ |
| **Authentication** | `POST` | `/auth/register` | สมัครสมาชิกใหม่ (บันทึกลง Postgres) |
| | `POST` | `/auth/login` | เข้าสู่ระบบและรับ JWT Access Token |
| | `GET` | `/auth/me` | ดึงข้อมูลโปรไฟล์ของ User ปัจจุบัน |
| | `POST` | `/auth/refresh` | ขอ Token ใหม่เมื่อ Token เดิมหมดอายุ |
| **Inference** | `POST` | `/inference/predict` | ส่งข้อความ/รูปภาพ เข้าโมเดล AI แล้วรับผลลัพธ์ |
| | `POST` | `/inference/predict/batch` | ประมวลผล input พร้อมกันหลายรายการ |
| | `GET` | `/inference/history` | ดูประวัติผลการทำนายของ User ตัวเอง |
| **Feedback** | `POST` | `/feedback/submit` | ส่งแจ้งผลการทำนายที่ผิด (สร้าง Task ใน Label Studio) |
| | `GET` | `/feedback/reviewed` | ดึงข้อมูลที่ Expert ตรวจสอบแล้วจาก Label Studio |
| **MLOps** | `GET` | `/mlops/models` | ดูรายการโมเดลและเวอร์ชันทั้งหมดที่มี |
| | `POST` | `/mlops/models/activate` | สลับโมเดลที่ต้องการใช้งาน (Blue-Green) |
| | `GET` | `/mlops/health` | ตรวจสอบสถานะการเชื่อมต่อ (Postgres, Redis, MinIO) |
| | `GET` | `/mlops/status` | เช็คสถานะระบบและโมเดลที่ใช้งานอยู่แบบเร็ว |

## การ Export รายการ API
คุณสามารถใช้สคริปต์เพื่อ Export รายการ API ทั้งหมดออกมาดูได้:
```bash
uv run python scripts/export_api_list.py
```
