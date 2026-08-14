# Core Infrastructure Layer (`core/`)

โฟลเดอร์ `core/` คือชั้น **Infrastructure Layer** ทำหน้าที่จัดการตั้งค่าและการเชื่อมต่อกับ External Services ต่างๆ ทั้งหมด 

> **สำคัญ:** โฟลเดอร์นี้จะต้องไม่มี Business Logic หรือโค้ดใดๆ ที่ผูกขาดกับฟีเจอร์ใดฟีเจอร์หนึ่ง หน้าที่เดียวของมันคือการต่อท่อและจัดเตรียมเครื่องมือให้ `app/features/` เรียกใช้งาน

## ทำไมต้องแยก Core ออกจาก Features?
เพื่อหลีกเลี่ยงการเขียนโค้ดเชื่อมต่อซ้ำซ้อน (Duplicated connection code) ตัวอย่างเช่น ทั้งระบบ `feedback` และฟีเจอร์อื่นๆ ในอนาคต อาจจะต้องการดึงข้อมูลจาก Label Studio ดังนั้นการแยก Label Studio Client ไว้ที่ `core/` จึงช่วยให้ทุกฟีเจอร์สามารถ Import ไปใช้งานร่วมกันได้ทันที โดยไม่ต้องตั้งค่าใหม่

## ส่วนประกอบภายใน `core/`

| ไฟล์ | บริการ/หน้าที่ที่เชื่อมต่อ | คำอธิบาย |
| --- | --- | --- |
| **`config.py`** | Environment | อ่านและตรวจสอบตัวแปรทั้งหมดจากไฟล์ `.env` (Source of truth เดียวของระบบ) |
| **`logger.py`** | System | ระบบ Custom Logging ที่จัดรูปแบบและบันทึก Log ลงไฟล์อย่างเป็นระเบียบ |
| **`database.py`** | PostgreSQL | สร้าง Database Engine, Sessions และ SQLAlchemy Declarative Base |
| **`minio_setup.py`**<br>**`minio_client.py`** | MinIO | เชื่อมต่อ MinIO (S3-compatible) รวมถึงสคริปต์ตรวจสอบการสร้าง Bucket เริ่มต้น |
| **`label_studio_client.py`**<br>**`label_studio_tasks.py`** | Label Studio | เชื่อมต่อผ่าน REST API จัดการ Import Tasks สำหรับทำ Annotation และ Export กลับมา |
