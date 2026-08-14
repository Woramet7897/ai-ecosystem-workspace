# Application Features Layer (`app/features/`)

โฟลเดอร์นี้จัดเก็บ Business Logic ของระบบทั้งหมด โดยออกแบบตาม **Feature-Based Architecture** แทนการใช้ Layer-Based Architecture (MVC) แบบดั้งเดิม

## ทำไมถึงใช้ Feature-Based Architecture?
* **High Cohesion:** โค้ดที่ทำงานเกี่ยวข้องกันถูกจัดเก็บไว้ในโฟลเดอร์เดียวกัน (เช่น ข้อมูลของ Auth ทั้งหมดจะอยู่ใน `auth/` ที่เดียว) ทำให้หาไฟล์ง่าย
* **Low Coupling:** แต่ละฟีเจอร์เป็นอิสระจากกัน (Self-contained) หากมีการแก้ไข Logic ของ Inference ก็จะไม่กระทบหรือลุกลามไปกวนฟีเจอร์อื่นๆ 
* **Easy to Scale:** เมื่อต้องการเพิ่มระบบย่อยใหม่ สามารถสร้างโฟลเดอร์ฟีเจอร์ใหม่ได้ทันทีโดยไม่ต้องกระจายแก้หลายไฟล์
* **Team Friendly:** นักพัฒนาสามารถแบ่งกันรับผิดชอบแยกตามฟีเจอร์ได้ชัดเจน ลดการเกิด Merge Conflicts

## มาตรฐานโครงสร้างไฟล์ในแต่ละฟีเจอร์
ทุกๆ ฟีเจอร์ที่ถูกสร้างขึ้นใหม่ (เช่น `auth`, `inference`, `feedback`) จะต้องมีไฟล์มาตรฐานดังนี้:

* `__init__.py`: ทำให้เป็น Python Package และ Expose `router` เพื่อให้ `main.py` นำไปใช้
* `router.py`: นิยาม API Endpoints, Dependencies (เช็คสิทธิ์), และจัดการ Request/Response
* `service.py`: รวม Business Logic, การคำนวณ, และการตัดสินใจทั้งหมด (ถูกเรียกใช้จาก `router.py`)
* `schemas.py`: Pydantic Models สำหรับทำ Data Validation ของ Request และ Response
* `models.py`: (ถ้ามี) SQLAlchemy Models สำหรับสร้างและจัดการ Table ใน Database

## ฟีเจอร์ที่พัฒนาแล้ว

* **`auth/`**: ระบบลงทะเบียน เข้าสู่ระบบ รหัสผ่าน และการจัดการ JWT (JSON Web Token) เพื่อควบคุมการเข้าถึง API
* **`inference/`**: ระบบจัดการการส่งข้อมูล (Text/Image) เข้าโมเดล AI เพื่อทำนายผลลัพธ์ พร้อมทั้งดูประวัติการทำนายของแต่ละ User
* **`feedback/`**: ระบบรับการแก้ไข (Correction) จากผู้ใช้เมื่อโมเดลทำนายผิดพลาด และทำงานร่วมกับ Label Studio เพื่อสร้างและดึง Annotation Tasks กลับมาใช้
* **`mlops/`**: ระบบหลังบ้านสำหรับแอดมินใช้ตรวจสอบ Health เช็คเวอร์ชันที่ Active และสลับการทำงานของโมเดล AI ในระบบ
