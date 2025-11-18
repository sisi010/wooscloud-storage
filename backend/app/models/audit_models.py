"""
Audit Log Models
Comprehensive activity tracking and monitoring
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# ============================================================================
# Enums
# ============================================================================

class AuditEventType(str, Enum):
    """Audit event types"""
    # Authentication
    AUTH_LOGIN = "auth.login"
    AUTH_LOGOUT = "auth.logout"
    AUTH_FAILED = "auth.failed"
    AUTH_API_KEY_CREATED = "auth.api_key_created"
    AUTH_API_KEY_DELETED = "auth.api_key_deleted"
    
    # Data Operations
    DATA_CREATE = "data.create"
    DATA_READ = "data.read"
    DATA_UPDATE = "data.update"
    DATA_DELETE = "data.delete"
    DATA_BULK_CREATE = "data.bulk_create"
    DATA_BULK_UPDATE = "data.bulk_update"
    DATA_BULK_DELETE = "data.bulk_delete"
    DATA_EXPORT = "data.export"
    
    # File Operations
    FILE_UPLOAD = "file.upload"
    FILE_DOWNLOAD = "file.download"
    FILE_DELETE = "file.delete"
    
    # Search Operations
    SEARCH_QUERY = "search.query"
    SEARCH_AUTOCOMPLETE = "search.autocomplete"
    
    # Backup Operations
    BACKUP_CREATE = "backup.create"
    BACKUP_DELETE = "backup.delete"
    BACKUP_RESTORE = "backup.restore"
    
    # Team Operations
    TEAM_ORG_CREATE = "team.org_create"
    TEAM_ORG_UPDATE = "team.org_update"
    TEAM_ORG_DELETE = "team.org_delete"
    TEAM_TEAM_CREATE = "team.team_create"
    TEAM_MEMBER_INVITE = "team.member_invite"
    TEAM_MEMBER_JOIN = "team.member_join"
    TEAM_MEMBER_REMOVE = "team.member_remove"
    
    # Webhook Operations
    WEBHOOK_CREATE = "webhook.create"
    WEBHOOK_UPDATE = "webhook.update"
    WEBHOOK_DELETE = "webhook.delete"
    WEBHOOK_TRIGGER = "webhook.trigger"
    
    # Security Events
    SECURITY_RATE_LIMIT = "security.rate_limit"
    SECURITY_UNAUTHORIZED = "security.unauthorized"
    SECURITY_FORBIDDEN = "security.forbidden"
    SECURITY_SUSPICIOUS = "security.suspicious"
    
    # System Events
    SYSTEM_ERROR = "system.error"
    SYSTEM_WARNING = "system.warning"

class AuditSeverity(str, Enum):
    """Audit event severity"""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class AuditStatus(str, Enum):
    """Audit event status"""
    SUCCESS = "success"
    FAILURE = "failure"
    PARTIAL = "partial"

# ============================================================================
# Audit Log Models
# ============================================================================

class AuditLogEntry(BaseModel):
    """Single audit log entry"""
    id: str
    user_id: str
    event_type: AuditEventType
    severity: AuditSeverity = AuditSeverity.INFO
    status: AuditStatus
    
    # Resource information
    resource_type: Optional[str] = None  # "data", "file", "backup", etc.
    resource_id: Optional[str] = None
    collection: Optional[str] = None
    
    # Request details
    method: str  # GET, POST, PUT, DELETE
    endpoint: str
    request_params: Optional[Dict[str, Any]] = {}
    request_body: Optional[Dict[str, Any]] = {}
    
    # Response details
    response_status: int
    response_time_ms: Optional[int] = None
    
    # Context
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    api_key_id: Optional[str] = None
    
    # Organization/Team context
    organization_id: Optional[str] = None
    team_id: Optional[str] = None
    
    # Changes (for update operations)
    changes: Optional[Dict[str, Any]] = {}
    
    # Additional metadata
    metadata: Dict[str, Any] = {}
    
    # Error information
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    
    # Timestamps
    timestamp: str
    created_at: str

class AuditLogFilter(BaseModel):
    """Filter for audit log queries"""
    user_id: Optional[str] = None
    event_type: Optional[AuditEventType] = None
    severity: Optional[AuditSeverity] = None
    status: Optional[AuditStatus] = None
    resource_type: Optional[str] = None
    collection: Optional[str] = None
    organization_id: Optional[str] = None
    team_id: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    ip_address: Optional[str] = None
    search: Optional[str] = None

class AuditLogListResponse(BaseModel):
    """List of audit logs"""
    logs: List[AuditLogEntry]
    total: int
    page: int
    page_size: int
    filters: Optional[Dict[str, Any]] = {}

# ============================================================================
# Statistics Models
# ============================================================================

class AuditStatsByEventType(BaseModel):
    """Statistics by event type"""
    event_type: str
    count: int
    success_count: int
    failure_count: int

class AuditStatsBySeverity(BaseModel):
    """Statistics by severity"""
    severity: str
    count: int

class AuditStatsByUser(BaseModel):
    """Statistics by user"""
    user_id: str
    total_events: int
    last_activity: str

class AuditStatsResponse(BaseModel):
    """Audit log statistics"""
    total_events: int
    date_range: Dict[str, str]
    by_event_type: List[AuditStatsByEventType]
    by_severity: List[AuditStatsBySeverity]
    by_status: Dict[str, int]
    top_users: List[AuditStatsByUser]
    unique_users: int
    unique_ips: int

# ============================================================================
# Security Events
# ============================================================================

class SecurityEvent(BaseModel):
    """Security event detection"""
    id: str
    severity: AuditSeverity
    event_type: AuditEventType
    user_id: Optional[str] = None
    ip_address: Optional[str] = None
    description: str
    details: Dict[str, Any] = {}
    detected_at: str
    resolved: bool = False
    resolved_at: Optional[str] = None

class SecurityEventListResponse(BaseModel):
    """List of security events"""
    events: List[SecurityEvent]
    total: int
    unresolved_count: int

# ============================================================================
# Export Models
# ============================================================================

class AuditLogExportRequest(BaseModel):
    """Export audit logs request"""
    format: str = Field("json", pattern="^(json|csv)$")
    filters: Optional[AuditLogFilter] = None
    include_metadata: bool = True

class AuditLogExportResponse(BaseModel):
    """Export response"""
    download_url: Optional[str] = None
    file_size_bytes: int
    record_count: int
    format: str
    expires_at: Optional[str] = None

# ============================================================================
# Activity Timeline
# ============================================================================

class ActivityTimelineEntry(BaseModel):
    """Single activity in timeline"""
    timestamp: str
    event_type: AuditEventType
    description: str
    user_id: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    status: AuditStatus

class ActivityTimelineResponse(BaseModel):
    """Activity timeline"""
    activities: List[ActivityTimelineEntry]
    total: int
    date_range: Dict[str, str]

# ============================================================================
# Real-time Monitoring
# ============================================================================

class SystemHealthMetrics(BaseModel):
    """System health metrics"""
    timestamp: str
    total_requests_last_hour: int
    success_rate: float
    average_response_time_ms: float
    error_rate: float
    active_users: int
    rate_limit_hits: int
    security_events: int

class UserActivitySummary(BaseModel):
    """User activity summary"""
    user_id: str
    total_actions: int
    last_activity: str
    most_common_actions: List[Dict[str, Any]]
    collections_accessed: List[str]