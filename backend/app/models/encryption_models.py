"""
Encryption Models
Pydantic models for encryption configuration
"""

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class EncryptionConfig(BaseModel):
    """Configuration for field-level encryption"""
    
    collection: str = Field(..., description="Collection name")
    fields: List[str] = Field(..., description="Fields to encrypt")
    enabled: bool = Field(default=True, description="Encryption enabled")
    
    class Config:
        json_schema_extra = {
            "example": {
                "collection": "users",
                "fields": ["ssn", "credit_card", "phone"],
                "enabled": True
            }
        }


class EncryptionSettings(BaseModel):
    """User encryption settings"""
    
    user_id: str
    enabled: bool = True
    encrypted_collections: List[str] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class EncryptFieldRequest(BaseModel):
    """Request to encrypt specific fields"""
    
    collection: str = Field(..., description="Collection name")
    document_id: str = Field(..., description="Document ID")
    fields: List[str] = Field(..., description="Fields to encrypt")
    
    class Config:
        json_schema_extra = {
            "example": {
                "collection": "users",
                "document_id": "507f1f77bcf86cd799439011",
                "fields": ["ssn", "phone"]
            }
        }


class EncryptFieldResponse(BaseModel):
    """Response after encrypting fields"""
    
    success: bool
    document_id: str
    encrypted_fields: List[str]
    message: str


class DecryptFieldRequest(BaseModel):
    """Request to decrypt specific fields"""
    
    collection: str = Field(..., description="Collection name")
    document_id: str = Field(..., description="Document ID")
    fields: Optional[List[str]] = Field(
        None,
        description="Fields to decrypt (None = auto-detect)"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "collection": "users",
                "document_id": "507f1f77bcf86cd799439011",
                "fields": ["ssn", "phone"]
            }
        }


class EncryptionStats(BaseModel):
    """Encryption statistics"""
    
    total_encrypted_fields: int
    collections_with_encryption: List[str]
    encryption_enabled: bool
    last_encryption: Optional[datetime] = None