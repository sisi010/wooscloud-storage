"""
Notification Models
Event-based notification system with multiple channels
"""

from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# ============================================================================
# Enums
# ============================================================================

class NotificationChannel(str, Enum):
    """Notification delivery channels"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    IN_APP = "in_app"

class NotificationPriority(str, Enum):
    """Notification priority levels"""
    URGENT = "urgent"      # Immediate
    HIGH = "high"          # Within 5 minutes
    NORMAL = "normal"      # Within 1 hour
    LOW = "low"            # Daily digest

class NotificationStatus(str, Enum):
    """Notification delivery status"""
    PENDING = "pending"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    READ = "read"

class NotificationEventType(str, Enum):
    """Notification event types"""
    # Backup events
    BACKUP_SUCCESS = "backup.success"
    BACKUP_FAILED = "backup.failed"
    BACKUP_SCHEDULE_CREATED = "backup.schedule_created"
    BACKUP_SCHEDULE_FAILED = "backup.schedule_failed"
    
    # Storage events
    STORAGE_QUOTA_WARNING = "storage.quota_warning"
    STORAGE_QUOTA_EXCEEDED = "storage.quota_exceeded"
    
    # Security events
    SECURITY_UNAUTHORIZED_ACCESS = "security.unauthorized_access"
    SECURITY_RATE_LIMIT = "security.rate_limit"
    SECURITY_API_KEY_CREATED = "security.api_key_created"
    
    # Team events
    TEAM_MEMBER_INVITED = "team.member_invited"
    TEAM_MEMBER_JOINED = "team.member_joined"
    TEAM_MEMBER_LEFT = "team.member_left"
    
    # System events
    SYSTEM_MAINTENANCE = "system.maintenance"
    SYSTEM_ERROR = "system.error"

# ============================================================================
# Notification Preferences
# ============================================================================

class NotificationPreferences(BaseModel):
    """User notification preferences"""
    user_id: str
    
    # Channel preferences
    email_enabled: bool = True
    webhook_enabled: bool = False
    in_app_enabled: bool = True
    
    # Email settings
    email_address: Optional[EmailStr] = None
    
    # Webhook settings
    webhook_url: Optional[str] = None
    
    # Event subscriptions (which events to receive)
    subscribed_events: List[NotificationEventType] = []
    
    # Priority filtering (minimum priority to receive)
    min_priority: NotificationPriority = NotificationPriority.NORMAL
    
    # Quiet hours
    quiet_hours_enabled: bool = False
    quiet_hours_start: Optional[str] = None  # "22:00"
    quiet_hours_end: Optional[str] = None    # "08:00"
    
    # Digest settings
    daily_digest_enabled: bool = False
    daily_digest_time: Optional[str] = None  # "09:00"

class NotificationPreferencesUpdate(BaseModel):
    """Update notification preferences"""
    email_enabled: Optional[bool] = None
    webhook_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None
    email_address: Optional[EmailStr] = None
    webhook_url: Optional[str] = None
    subscribed_events: Optional[List[NotificationEventType]] = None
    min_priority: Optional[NotificationPriority] = None
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None
    daily_digest_enabled: Optional[bool] = None
    daily_digest_time: Optional[str] = None

# ============================================================================
# Notification Models
# ============================================================================

class NotificationCreate(BaseModel):
    """Create notification request"""
    event_type: NotificationEventType
    priority: NotificationPriority = NotificationPriority.NORMAL
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=2000)
    data: Optional[Dict[str, Any]] = {}
    action_url: Optional[str] = None
    channels: Optional[List[NotificationChannel]] = None  # None = all enabled

class Notification(BaseModel):
    """Notification model"""
    id: str
    user_id: str
    event_type: NotificationEventType
    priority: NotificationPriority
    
    # Content
    title: str
    message: str
    data: Dict[str, Any] = {}
    action_url: Optional[str] = None
    
    # Delivery
    channels: List[NotificationChannel]
    status: NotificationStatus
    
    # Timestamps
    created_at: str
    sent_at: Optional[str] = None
    delivered_at: Optional[str] = None
    read_at: Optional[str] = None
    
    # Metadata
    error_message: Optional[str] = None
    retry_count: int = 0

class NotificationListResponse(BaseModel):
    """List of notifications"""
    notifications: List[Notification]
    total: int
    unread_count: int
    page: int
    page_size: int

# ============================================================================
# Notification Templates
# ============================================================================

class NotificationTemplate(BaseModel):
    """Notification template"""
    event_type: NotificationEventType
    title_template: str
    message_template: str
    default_priority: NotificationPriority
    
    # Template variables (for documentation)
    variables: List[str] = []

# Predefined templates
NOTIFICATION_TEMPLATES = {
    NotificationEventType.BACKUP_SUCCESS: NotificationTemplate(
        event_type=NotificationEventType.BACKUP_SUCCESS,
        title_template="✅ Backup Completed Successfully",
        message_template="Your backup '{backup_name}' has completed successfully. {record_count} records backed up ({size_mb} MB).",
        default_priority=NotificationPriority.LOW,
        variables=["backup_name", "record_count", "size_mb"]
    ),
    NotificationEventType.BACKUP_FAILED: NotificationTemplate(
        event_type=NotificationEventType.BACKUP_FAILED,
        title_template="❌ Backup Failed",
        message_template="Your backup '{backup_name}' has failed. Error: {error_message}",
        default_priority=NotificationPriority.HIGH,
        variables=["backup_name", "error_message"]
    ),
    NotificationEventType.BACKUP_SCHEDULE_FAILED: NotificationTemplate(
        event_type=NotificationEventType.BACKUP_SCHEDULE_FAILED,
        title_template="⚠️ Scheduled Backup Failed",
        message_template="Scheduled backup '{schedule_name}' failed to execute. Error: {error_message}",
        default_priority=NotificationPriority.URGENT,
        variables=["schedule_name", "error_message"]
    ),
    NotificationEventType.STORAGE_QUOTA_WARNING: NotificationTemplate(
        event_type=NotificationEventType.STORAGE_QUOTA_WARNING,
        title_template="⚠️ Storage Quota Warning",
        message_template="You have used {used_percentage}% of your storage quota. Consider upgrading your plan.",
        default_priority=NotificationPriority.NORMAL,
        variables=["used_percentage", "used_mb", "total_mb"]
    ),
    NotificationEventType.STORAGE_QUOTA_EXCEEDED: NotificationTemplate(
        event_type=NotificationEventType.STORAGE_QUOTA_EXCEEDED,
        title_template="🚨 Storage Quota Exceeded",
        message_template="You have exceeded your storage quota. Please upgrade your plan or delete some data.",
        default_priority=NotificationPriority.URGENT,
        variables=["used_mb", "total_mb"]
    ),
    NotificationEventType.SECURITY_UNAUTHORIZED_ACCESS: NotificationTemplate(
        event_type=NotificationEventType.SECURITY_UNAUTHORIZED_ACCESS,
        title_template="🔒 Unauthorized Access Attempt",
        message_template="An unauthorized access attempt was detected from IP {ip_address} at {timestamp}.",
        default_priority=NotificationPriority.URGENT,
        variables=["ip_address", "timestamp", "endpoint"]
    ),
    NotificationEventType.TEAM_MEMBER_INVITED: NotificationTemplate(
        event_type=NotificationEventType.TEAM_MEMBER_INVITED,
        title_template="👥 Team Invitation",
        message_template="You have been invited to join '{organization_name}' as a {role}.",
        default_priority=NotificationPriority.NORMAL,
        variables=["organization_name", "role", "invited_by"]
    ),
    NotificationEventType.TEAM_MEMBER_JOINED: NotificationTemplate(
        event_type=NotificationEventType.TEAM_MEMBER_JOINED,
        title_template="👋 New Team Member",
        message_template="{member_name} has joined your organization '{organization_name}'.",
        default_priority=NotificationPriority.LOW,
        variables=["member_name", "organization_name", "role"]
    )
}

# ============================================================================
# Statistics Models
# ============================================================================

class NotificationStats(BaseModel):
    """Notification statistics"""
    total_sent: int
    total_delivered: int
    total_failed: int
    total_read: int
    total_unread: int
    by_channel: Dict[str, int]
    by_priority: Dict[str, int]
    by_event_type: Dict[str, int]
    delivery_rate: float
    read_rate: float

# ============================================================================
# Batch Notification
# ============================================================================

class BatchNotificationCreate(BaseModel):
    """Create notifications for multiple users"""
    user_ids: List[str]
    event_type: NotificationEventType
    priority: NotificationPriority = NotificationPriority.NORMAL
    title: str = Field(min_length=1, max_length=200)
    message: str = Field(min_length=1, max_length=2000)
    data: Optional[Dict[str, Any]] = {}
    action_url: Optional[str] = None

class BatchNotificationResponse(BaseModel):
    """Batch notification response"""
    created_count: int
    failed_count: int
    notification_ids: List[str]