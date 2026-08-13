"""
security.py - Security & Auth API
ด้านที่ 4: Token Verification, Rate Limiting, Usage Quota

เป็น module แรกที่ต้อง import ก่อน module อื่น
เพราะ verify_token ถูกใช้เป็น Depends() ในทุก Router
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from typing import Optional
import time
import hashlib

from core.logger import setup_custom_logger

logger = setup_custom_logger("security")

router = APIRouter(
    prefix="/security",
    tags=["Security"],
)

# ──────────────────────────────────────────────
# [MOCK] User Store
# TODO: แทนที่ด้วย database จริง (PostgreSQL + bcrypt hashed password)
# ──────────────────────────────────────────────
USER_DB = {
    "admin":     {"password": "admin1234",  "role": "admin"},
    "developer": {"password": "dev1234",    "role": "user"},
}

# [MOCK] Token Store
# TODO: แทนที่ด้วย Redis หรือ JWT จริง
# ──────────────────────────────────────────────
VALID_TOKENS = {
    "dev-token-001":  {"user": "developer", "quota": 1000, "used": 12},
    "test-token-002": {"user": "tester",    "quota": 500,  "used": 5},
}

# ──────────────────────────────────────────────
# Dependency Function
# ──────────────────────────────────────────────

# ใช้ APIKeyHeader ให้ Swagger UI แสดงปุ่ม Authorize และส่ง header ได้ถูกต้อง
api_key_scheme = APIKeyHeader(name="X-Token", auto_error=False)

def verify_token(token: Optional[str] = Depends(api_key_scheme)) -> str:
    """
    Dependency ตรวจสอบ token จาก Header: X-Token: <token>
    กด Authorize บน Swagger UI แล้วใส่ token ได้เลย

    [MOCK] ตรวจสอบจาก VALID_TOKENS dict
    TODO: ต่อกับ database หรือ JWT จริง
    """
    if token and token in VALID_TOKENS:
        return token
    return "anonymous"


# ──────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────

class LoginRequest(BaseModel):
    """Schema สำหรับ Login"""
    username: str = Field(..., description="ชื่อผู้ใช้")
    password: str = Field(..., description="รหัสผ่าน")

    class Config:
        json_schema_extra = {"example": {"username": "admin", "password": "admin1234"}}

class LoginResponse(BaseModel):
    """Schema สำหรับ response หลัง Login สำเร็จ"""
    access_token: str = Field(..., description="Token สำหรับใช้ใน Authorization header")
    token_type:   str = Field("bearer", description="ประเภทของ token")
    username:     str = Field(..., description="ชื่อผู้ใช้ที่ login สำเร็จ")
    role:         str = Field(..., description="สิทธิ์ของผู้ใช้ (admin/user)")

class TokenCheckResponse(BaseModel):
    valid:    bool = Field(..., description="token ถูกต้องหรือไม่")
    user:     str  = Field(..., description="ชื่อผู้ใช้ที่ผูกกับ token นี้")
    message:  str  = Field(..., description="ข้อความอธิบายผลการตรวจสอบ")

class UsageResponse(BaseModel):
    token:     str = Field(..., description="token ที่ใช้ตรวจสอบ")
    user:      str = Field(..., description="ชื่อผู้ใช้")
    quota:     int = Field(..., description="จำนวน request สูงสุดที่ได้รับอนุญาต")
    used:      int = Field(..., description="จำนวน request ที่ใช้ไปแล้ว")
    remaining: int = Field(..., description="จำนวน request ที่เหลือ")


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.post(
    "/login",
    response_model=LoginResponse,
    summary="เข้าสู่ระบบ - รับ Token สำหรับใช้งาน API",
    description="เข้าสู่ระบบด้วย username/password แล้วรับ access_token สำหรับใช้เรียก API อื่นๆ",
)
def login(req: LoginRequest):
    """
    POST /security/login

    ขั้นตอน Authentication:
    1. รับ username + password จาก client
    2. ตรวจสอบกับ USER_DB
    3. ถ้าถูกต้อง → สร้าง token แล้วคืนกลับ
    4. client นำ token ไปใส่ใน Header: Authorization: Bearer <token>

    [MOCK] ตรวจสอบจาก USER_DB dict ใน memory
    TODO: ต่อกับ PostgreSQL จริง + ใช้ bcrypt verify password + ออก JWT token
    """
    logger.info(f"[login] username={req.username}")

    # ตรวจสอบ username มีในระบบหรือไม่
    if req.username not in USER_DB:
        raise HTTPException(status_code=401, detail="username หรือ password ไม่ถูกต้อง")

    # ตรวจสอบ password
    # [MOCK] เปรียบเทียบ plain text ตรงๆ
    # TODO: ใช้ bcrypt.checkpw(password, hashed) แทน
    if USER_DB[req.username]["password"] != req.password:
        raise HTTPException(status_code=401, detail="username หรือ password ไม่ถูกต้อง")

    # สร้าง Token
    # [MOCK] ใช้ hashlib สร้าง token อย่างง่าย
    # TODO: ออก JWT จริงด้วย python-jose หรือ PyJWT
    raw = f"{req.username}:{int(time.time())}"
    token = hashlib.sha256(raw.encode()).hexdigest()[:32]

    # บันทึก token ไว้ใน VALID_TOKENS (ชั่วคราว)
    VALID_TOKENS[token] = {"user": req.username, "quota": 1000, "used": 0}

    logger.info(f"[login] login success for user={req.username} role={USER_DB[req.username]['role']}")

    return LoginResponse(
        access_token=token,
        token_type="bearer",
        username=req.username,
        role=USER_DB[req.username]["role"],
    )

@router.get(
    "/check-token",
    response_model=TokenCheckResponse,
    summary="ตรวจสอบว่า Token ถูกต้องหรือไม่",
    description="ตรวจสอบว่า token ที่ส่งมาใน Authorization header ถูกต้องและยังใช้งานได้หรือไม่",
)
def check_token(token: str = Depends(verify_token)):
    """
    GET /security/check-token

    ตรวจสอบ token ที่ส่งมาใน Header: Authorization: Bearer <token>
    คืนผลลัพธ์ว่า token ถูกต้องหรือไม่ พร้อมข้อมูลผู้ใช้

    [MOCK] ตรวจสอบจาก VALID_TOKENS dict ใน memory
    TODO: ต่อกับ Auth service จริง เช่น Keycloak, Auth0, หรือ JWT verify
    """
    logger.info(f"[check-token] token={token[:12]}...")

    if token in VALID_TOKENS:
        user_info = VALID_TOKENS[token]
        return TokenCheckResponse(valid=True, user=user_info["user"], message="Token ถูกต้อง")

    return TokenCheckResponse(valid=False, user="anonymous", message="[MOCK] Token ไม่พบในระบบ หรืออยู่ใน dev mode")


@router.get(
    "/usage",
    response_model=UsageResponse,
    summary="ดูการใช้งานและ Quota ที่เหลือ",
    description="เช็ค rate limit และ usage quota ที่เหลืออยู่ของ token นี้",
)
def check_usage(token: str = Depends(verify_token)):
    """
    GET /security/usage

    ดูสถานะการใช้งาน quota ของ token ปัจจุบัน
    ใช้สำหรับ client ตรวจสอบว่ายังมี quota เหลืออยู่ก่อน predict

    [MOCK] คืนค่าจาก VALID_TOKENS dict
    TODO: ต่อกับ Redis หรือ database เพื่อนับ request จริง
    """
    logger.info(f"[usage] checking quota for token={token}")

    if token in VALID_TOKENS:
        info = VALID_TOKENS[token]
        return UsageResponse(
            token=token,
            user=info["user"],
            quota=info["quota"],
            used=info["used"],
            remaining=info["quota"] - info["used"],
        )

    # [MOCK] Dev mode: คืนค่า unlimited
    return UsageResponse(
        token="anonymous",
        user="anonymous (dev mode)",
        quota=9999,
        used=0,
        remaining=9999,
    )
