"""
V2 API Models
Improved response structure and consistency
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional, Union
from datetime import datetime

# ============================================================================
# Base Response Models
# ============================================================================

class V2Response(BaseModel):
    """
    Standard V2 API response format
    
    All V2 responses follow this consistent structure
    """
    success: bool = Field(description="Whether the request was successful")
    data: Optional[Any] = Field(None, description="Response data")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details if failed")
    meta: Optional[Dict[str, Any]] = Field(None, description="Metadata about the response")


class V2Error(BaseModel):
    """V2 Error format"""
    code: str = Field(description="Error code (e.g., 'NOT_FOUND', 'VALIDATION_ERROR')")
    message: str = Field(description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class V2Meta(BaseModel):
    """V2 Metadata format"""
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    request_id: Optional[str] = None
    api_version: str = "v2"
    deprecation_warning: Optional[str] = None


# ============================================================================
# Pagination
# ============================================================================

class V2Pagination(BaseModel):
    """Improved pagination model"""
    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, le=100, description="Items per page")
    total_items: int = Field(ge=0, description="Total number of items")
    total_pages: int = Field(ge=0, description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")


# ============================================================================
# Storage Data Models
# ============================================================================

class V2StorageData(BaseModel):
    """V2 Storage data format"""
    id: str = Field(description="Unique identifier")
    collection: str = Field(description="Collection name")
    data: Dict[str, Any] = Field(description="User data")
    metadata: Dict[str, Any] = Field(description="System metadata")
    created_at: str = Field(description="Creation timestamp (ISO 8601)")
    updated_at: str = Field(description="Last update timestamp (ISO 8601)")
    version: int = Field(default=1, description="Data version number")


class V2StorageDataList(BaseModel):
    """V2 list response"""
    items: List[V2StorageData]
    pagination: V2Pagination
    filters_applied: Optional[Dict[str, Any]] = None


class V2CreateRequest(BaseModel):
    """V2 create data request"""
    collection: str = Field(min_length=1, max_length=100)
    data: Dict[str, Any]
    tags: Optional[List[str]] = Field(None, max_items=10)
    metadata: Optional[Dict[str, Any]] = None


class V2UpdateRequest(BaseModel):
    """V2 update data request"""
    data: Dict[str, Any]
    merge: bool = Field(default=True, description="Merge with existing data or replace")
    increment_version: bool = Field(default=True, description="Increment version number")


# ============================================================================
# Batch Operations
# ============================================================================

class V2BatchCreateRequest(BaseModel):
    """V2 batch create request"""
    collection: str
    items: List[Dict[str, Any]] = Field(max_items=100)
    stop_on_error: bool = Field(default=False, description="Stop on first error")


class V2BatchResult(BaseModel):
    """V2 batch operation result"""
    successful: int = Field(description="Number of successful operations")
    failed: int = Field(description="Number of failed operations")
    results: List[Dict[str, Any]] = Field(description="Individual results")
    errors: List[Dict[str, Any]] = Field(description="Error details")


# ============================================================================
# Search Models
# ============================================================================

class V2SearchRequest(BaseModel):
    """V2 search request"""
    query: str = Field(min_length=1)
    collections: Optional[List[str]] = Field(None, description="Collections to search in")
    fields: Optional[List[str]] = Field(None, description="Fields to search")
    filters: Optional[Dict[str, Any]] = None
    sort_by: Optional[str] = None
    sort_order: Optional[str] = Field("desc", pattern="^(asc|desc)$")
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)


class V2SearchResult(BaseModel):
    """V2 search result"""
    items: List[V2StorageData]
    pagination: V2Pagination
    facets: Optional[Dict[str, Any]] = Field(None, description="Search facets/aggregations")
    query_time_ms: float = Field(description="Query execution time in milliseconds")


# ============================================================================
# Statistics Models
# ============================================================================

class V2Stats(BaseModel):
    """V2 statistics format"""
    storage: Dict[str, Any] = Field(description="Storage usage statistics")
    api_calls: Dict[str, Any] = Field(description="API call statistics")
    collections: Dict[str, Any] = Field(description="Collection statistics")
    plan: Dict[str, Any] = Field(description="Plan information")
    period: Dict[str, Any] = Field(description="Statistics period")


# ============================================================================
# File Models
# ============================================================================

class V2FileInfo(BaseModel):
    """V2 file information"""
    id: str
    filename: str
    content_type: str
    size_bytes: int
    collection: str
    url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str


class V2FileUploadResponse(BaseModel):
    """V2 file upload response"""
    file: V2FileInfo
    upload_time_ms: float


# ============================================================================
# Webhook Models
# ============================================================================

class V2WebhookConfig(BaseModel):
    """V2 webhook configuration"""
    id: str
    url: str
    events: List[str]
    secret: str
    is_active: bool
    retry_policy: Dict[str, Any] = Field(description="Retry configuration")
    headers: Optional[Dict[str, str]] = Field(None, description="Custom headers")
    created_at: str
    updated_at: str
    stats: Dict[str, Any] = Field(description="Webhook statistics")


# ============================================================================
# Export Models
# ============================================================================

class V2ExportRequest(BaseModel):
    """V2 export request"""
    collection: str
    format: str = Field(pattern="^(json|csv|xlsx|parquet)$")
    filters: Optional[Dict[str, Any]] = None
    fields: Optional[List[str]] = None
    compression: Optional[str] = Field(None, pattern="^(gzip|zip)$")


class V2ExportJob(BaseModel):
    """V2 export job status"""
    job_id: str
    status: str = Field(description="pending, processing, completed, failed")
    collection: str
    format: str
    progress_percent: float = Field(ge=0, le=100)
    records_processed: int
    download_url: Optional[str] = None
    expires_at: Optional[str] = None
    created_at: str
    updated_at: str