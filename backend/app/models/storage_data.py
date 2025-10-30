"""
Storage data model
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class StorageDataCreate(BaseModel):
    """Storage data creation model"""
    collection: str = Field(..., min_length=1, max_length=100)
    data: Dict[str, Any]

class StorageDataUpdate(BaseModel):
    """Storage data update model"""
    data: Dict[str, Any]

class StorageData(BaseModel):
    """Storage data model with all fields"""
    id: str = Field(alias="_id")
    user_id: str
    collection: str
    data: Dict[str, Any]
    size: int  # bytes
    provider: str = "mongodb"  # "mongodb", "supabase", "firebase" (Phase 2+)
    created_at: datetime
    updated_at: datetime
    
    class Config:
        populate_by_name = True

class StorageStats(BaseModel):
    """Storage statistics model"""
    used: int  # bytes
    limit: int  # bytes
    percent: float
    plan: str
    api_calls_count: int
    api_calls_limit: int