"""
Batch operation models
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class BatchCreateItem(BaseModel):
    """Single item for batch create"""
    collection: str = Field(..., description="Collection name")
    data: Dict[str, Any] = Field(..., description="Data to store")

class BatchCreateRequest(BaseModel):
    """Batch create request"""
    items: List[BatchCreateItem] = Field(..., description="Items to create", max_length=100)

class BatchCreateResponse(BaseModel):
    """Batch create response"""
    success: bool = True
    created: int
    items: List[Dict[str, Any]]
    failed: List[Dict[str, Any]] = []

class BatchReadRequest(BaseModel):
    """Batch read request"""
    ids: List[str] = Field(..., description="IDs to read", max_length=100)

class BatchReadResponse(BaseModel):
    """Batch read response"""
    success: bool = True
    found: int
    items: List[Dict[str, Any]]
    not_found: List[str] = []

class BatchUpdateItem(BaseModel):
    """Single item for batch update"""
    id: str = Field(..., description="Item ID")
    data: Dict[str, Any] = Field(..., description="New data")

class BatchUpdateRequest(BaseModel):
    """Batch update request"""
    items: List[BatchUpdateItem] = Field(..., description="Items to update", max_length=100)

class BatchUpdateResponse(BaseModel):
    """Batch update response"""
    success: bool = True
    updated: int
    items: List[Dict[str, Any]]
    failed: List[Dict[str, Any]] = []

class BatchDeleteRequest(BaseModel):
    """Batch delete request"""
    ids: List[str] = Field(..., description="IDs to delete", max_length=100)

class BatchDeleteResponse(BaseModel):
    """Batch delete response"""
    success: bool = True
    deleted: int
    ids: List[str]
    not_found: List[str] = []