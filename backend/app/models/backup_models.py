"""
Backup & Restore Models
Advanced backup system with incremental, scheduled, and point-in-time recovery
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# ============================================================================
# Enums
# ============================================================================

class BackupType(str, Enum):
    """Backup types"""
    FULL = "full"
    INCREMENTAL = "incremental"
    DIFFERENTIAL = "differential"

class BackupStatus(str, Enum):
    """Backup job status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class RestoreStatus(str, Enum):
    """Restore job status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class ConflictResolution(str, Enum):
    """How to handle conflicts during restore"""
    SKIP = "skip"
    OVERWRITE = "overwrite"
    RENAME = "rename"

class BackupSchedule(str, Enum):
    """Backup schedule frequency"""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"

# ============================================================================
# Backup Request/Response Models
# ============================================================================

class BackupCreateRequest(BaseModel):
    """Create backup request"""
    name: Optional[str] = Field(None, description="Backup name")
    description: Optional[str] = Field(None, description="Backup description")
    backup_type: BackupType = Field(BackupType.FULL, description="Backup type")
    collections: Optional[List[str]] = Field(None, description="Specific collections (None = all)")
    include_files: bool = Field(True, description="Include file attachments")
    compress: bool = Field(True, description="Compress backup")
    tags: Optional[List[str]] = Field(None, max_items=10)

class BackupMetadata(BaseModel):
    """Backup metadata"""
    id: str
    name: str
    user_id: str
    backup_type: BackupType
    status: BackupStatus
    collections: List[str]
    include_files: bool
    compressed: bool
    size_bytes: int = 0
    file_count: int = 0
    record_count: int = 0
    created_at: str
    completed_at: Optional[str] = None
    expires_at: Optional[str] = None
    download_url: Optional[str] = None
    tags: List[str] = []
    error_message: Optional[str] = None

class BackupListResponse(BaseModel):
    """List of backups"""
    backups: List[BackupMetadata]
    total: int
    page: int
    page_size: int

class BackupStatsResponse(BaseModel):
    """Backup statistics"""
    total_backups: int
    total_size_bytes: int
    latest_backup: Optional[BackupMetadata] = None
    oldest_backup: Optional[BackupMetadata] = None
    by_type: Dict[str, int]
    by_status: Dict[str, int]

# ============================================================================
# Restore Request/Response Models
# ============================================================================

class RestoreRequest(BaseModel):
    """Restore from backup request"""
    backup_id: str = Field(description="Backup ID to restore from")
    collections: Optional[List[str]] = Field(None, description="Specific collections (None = all)")
    point_in_time: Optional[str] = Field(None, description="Restore to specific timestamp (ISO 8601)")
    conflict_resolution: ConflictResolution = Field(
        ConflictResolution.SKIP, 
        description="How to handle conflicts"
    )
    restore_files: bool = Field(True, description="Restore file attachments")
    dry_run: bool = Field(False, description="Simulate restore without applying")

class RestoreJobMetadata(BaseModel):
    """Restore job metadata"""
    id: str
    backup_id: str
    user_id: str
    status: RestoreStatus
    collections: List[str]
    conflict_resolution: ConflictResolution
    dry_run: bool
    records_restored: int = 0
    files_restored: int = 0
    conflicts_encountered: int = 0
    conflicts_resolved: Dict[str, int] = {}  # skip/overwrite/rename counts
    created_at: str
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    preview: Optional[Dict[str, Any]] = None  # For dry_run

# ============================================================================
# Scheduled Backup Models
# ============================================================================

class BackupScheduleConfig(BaseModel):
    """Scheduled backup configuration"""
    enabled: bool = True
    schedule: BackupSchedule
    time_of_day: str = Field("02:00", description="Time in HH:MM format")
    day_of_week: Optional[int] = Field(None, ge=0, le=6, description="0=Monday, 6=Sunday")
    day_of_month: Optional[int] = Field(None, ge=1, le=31)
    backup_type: BackupType = BackupType.FULL
    collections: Optional[List[str]] = None
    include_files: bool = True
    compress: bool = True
    retention_days: int = Field(30, ge=1, le=365, description="Keep backups for N days")

class ScheduledBackupInfo(BaseModel):
    """Scheduled backup information"""
    id: str
    user_id: str
    config: BackupScheduleConfig
    last_run: Optional[str] = None
    next_run: str
    run_count: int = 0
    created_at: str
    updated_at: str

# ============================================================================
# Incremental Backup Models
# ============================================================================

class IncrementalBackupInfo(BaseModel):
    """Incremental backup information"""
    baseline_backup_id: str = Field(description="Base full backup")
    changes_since: str = Field(description="Timestamp of baseline")
    added_records: int = 0
    modified_records: int = 0
    deleted_records: int = 0

# ============================================================================
# Backup Content Models
# ============================================================================

class BackupManifest(BaseModel):
    """Backup manifest (stored in backup file)"""
    backup_id: str
    backup_type: BackupType
    created_at: str
    user_id: str
    collections: List[str]
    record_count: int
    file_count: int
    compressed: bool
    incremental_info: Optional[IncrementalBackupInfo] = None
    checksums: Dict[str, str] = {}  # collection -> checksum

class BackupRecord(BaseModel):
    """Individual record in backup"""
    collection: str
    record_id: str
    data: Dict[str, Any]
    metadata: Dict[str, Any]
    files: List[str] = []  # Associated file IDs
    backed_up_at: str

# ============================================================================
# Point-in-Time Recovery Models
# ============================================================================

class PITRSnapshot(BaseModel):
    """Point-in-time recovery snapshot"""
    timestamp: str
    backup_id: str
    available_collections: List[str]
    record_count: int

class PITRHistoryResponse(BaseModel):
    """PITR history"""
    snapshots: List[PITRSnapshot]
    earliest_available: str
    latest_available: str
    total_snapshots: int