from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models.user import UserRole

class UserProfileBase(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=255)
    phone_number: Optional[str] = Field(None, max_length=50)
    city: Optional[str] = Field(None, max_length=100)
    preferred_language: str = Field(default="English", max_length=50)

class UserProfileResponse(UserProfileBase):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6, max_length=128)
    full_name: str = Field(..., min_length=2, max_length=255)
    role: UserRole = Field(default=UserRole.USER)
    phone_number: Optional[str] = None
    city: Optional[str] = None
    preferred_language: Optional[str] = "English"

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserResponse(BaseModel):
    id: int
    email: str
    role: UserRole
    is_active: bool
    profile: Optional[UserProfileResponse] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
