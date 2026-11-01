from typing import Optional
from pydantic import BaseModel, EmailStr, Field


class CaptchaResponse(BaseModel):
    captcha_id: str
    image_base64: str


class LoginRequest(BaseModel):
    role: str = Field(..., description="INSTITUTE or ADMIN")
    institute_name: Optional[str] = None
    institute_id: Optional[str] = None
    identifier: Optional[str] = None
    password: str = Field(..., min_length=1)
    captcha_id: str
    captcha_text: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    role: str = Field(default="INSTITUTE")
    aicte_institute_id: Optional[str] = None
    institute_name: Optional[str] = None
    state: Optional[str] = None


class InstituteInfo(BaseModel):
    id: int
    aicte_institute_id: str
    name: str
    state: str
    status: str

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    region: Optional[str] = None
    institute: Optional[InstituteInfo] = None

    class Config:
        from_attributes = True


class LoginResponse(BaseModel):
    message: str = "Login successful"
    user: UserResponse
    csrf_token: str


class TokenRefreshResponse(BaseModel):
    message: str = "Token refreshed successfully"
    csrf_token: str


class MessageResponse(BaseModel):
    message: str

