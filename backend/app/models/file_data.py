"""
File data models
"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime

class FileUploadResponse(BaseModel):
    """File upload response"""
    success: bool = True
    id: str
    filename: str
    content_type: str
    size: int
    storage_type: str  # 'mongodb' or 'r2'
    url: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: str

class FileInfo(BaseModel):
    """File information"""
    id: str
    filename: str
    content_type: str
    size: int
    storage_type: str
    collection: str
    metadata: Optional[Dict[str, Any]] = None
    created_at: str
    updated_at: str

class FileMetadata(BaseModel):
    """File metadata for upload"""
    collection: str = Field(..., description="Collection name")
    description: Optional[str] = Field(None, description="File description")
    tags: Optional[list[str]] = Field(default=[], description="File tags")
    custom: Optional[Dict[str, Any]] = Field(default={}, description="Custom metadata")