"""
User model
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    """Base user model"""
    email: EmailStr
    name: str

class UserCreate(UserBase):
    """User creation model"""
    password: str

class UserLogin(BaseModel):
    """User login model"""
    email: EmailStr
    password: str

class User(UserBase):
    """User model with all fields"""
    id: str = Field(alias="_id")
    plan: str = "free"  # "free", "starter", "pro"
    storage_used: int = 0  # bytes
    storage_limit: int = 500 * 1024 * 1024  # 500MB default
    api_calls_count: int = 0
    api_calls_limit: int = 10000
    created_at: datetime
    updated_at: datetime
    is_active: bool = True
    
    class Config:
        populate_by_name = True

class Token(BaseModel):
    """JWT token model"""
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    """Token payload data"""
    email: Optional[str] = None