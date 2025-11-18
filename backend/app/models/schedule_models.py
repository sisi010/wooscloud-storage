"""
Backup Schedule Models
Automatic backup scheduling with retention policies
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

# ============================================================================
# Enums
# ============================================================================

class ScheduleFrequency(str, Enum):
    """Schedule frequency presets"""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CUSTOM = "custom"  # Use cron expression

class ScheduleStatus(str, Enum):
    """Schedule status"""
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"

class BackupJobStatus(str, Enum):
    """Backup job execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

# ============================================================================
# Schedule Models
# ============================================================================

class BackupScheduleCreate(BaseModel):
    """Create backup schedule request"""
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    
    # Schedule configuration
    frequency: ScheduleFrequency
    cron_expression: Optional[str] = None  # For CUSTOM frequency
    timezone: str = "UTC"
    
    # Backup configuration
    backup_type: str = Field("full", pattern="^(full|incremental)$")
    collections: Optional[List[str]] = None  # None = all collections
    include_files: bool = True
    compress: bool = True
    
    # Retention policy
    retention_days: Optional[int] = Field(None, ge=1, le=365)
    max_backups: Optional[int] = Field(None, ge=1, le=100)
    
    # Metadata
    tags: List[str] = []
    
    @validator("cron_expression")
    def validate_cron(cls, v, values):
        """Validate cron expression for CUSTOM frequency"""
        if values.get("frequency") == ScheduleFrequency.CUSTOM and not v:
            raise ValueError("cron_expression required for CUSTOM frequency")
        return v

class BackupScheduleUpdate(BaseModel):
    """Update backup schedule request"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    frequency: Optional[ScheduleFrequency] = None
    cron_expression: Optional[str] = None
    timezone: Optional[str] = None
    backup_type: Optional[str] = Field(None, pattern="^(full|incremental)$")
    collections: Optional[List[str]] = None
    include_files: Optional[bool] = None
    compress: Optional[bool] = None
    retention_days: Optional[int] = Field(None, ge=1, le=365)
    max_backups: Optional[int] = Field(None, ge=1, le=100)
    status: Optional[ScheduleStatus] = None
    tags: Optional[List[str]] = None

class BackupSchedule(BaseModel):
    """Backup schedule model"""
    id: str
    user_id: str
    name: str
    description: Optional[str] = None
    
    # Schedule
    frequency: ScheduleFrequency
    cron_expression: Optional[str] = None
    timezone: str
    status: ScheduleStatus
    
    # Backup config
    backup_type: str
    collections: Optional[List[str]] = None
    include_files: bool
    compress: bool
    
    # Retention
    retention_days: Optional[int] = None
    max_backups: Optional[int] = None
    
    # Execution tracking
    last_run_at: Optional[str] = None
    last_run_status: Optional[BackupJobStatus] = None
    next_run_at: Optional[str] = None
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    
    # Metadata
    tags: List[str] = []
    created_at: str
    updated_at: str

class BackupScheduleListResponse(BaseModel):
    """List of backup schedules"""
    schedules: List[BackupSchedule]
    total: int

# ============================================================================
# Backup Job Models
# ============================================================================

class BackupJob(BaseModel):
    """Backup job execution record"""
    id: str
    schedule_id: str
    user_id: str
    backup_id: Optional[str] = None  # Created backup ID
    
    status: BackupJobStatus
    
    # Execution details
    started_at: str
    completed_at: Optional[str] = None
    duration_seconds: Optional[int] = None
    
    # Results
    records_backed_up: int = 0
    size_bytes: int = 0
    
    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    # Metadata
    metadata: Dict[str, Any] = {}

class BackupJobListResponse(BaseModel):
    """List of backup jobs"""
    jobs: List[BackupJob]
    total: int
    page: int
    page_size: int

# ============================================================================
# Statistics Models
# ============================================================================

class ScheduleStatistics(BaseModel):
    """Schedule execution statistics"""
    schedule_id: str
    total_runs: int
    successful_runs: int
    failed_runs: int
    skipped_runs: int
    success_rate: float
    average_duration_seconds: float
    last_7_days_runs: int
    total_data_backed_up_bytes: int

class ScheduleHealthStatus(BaseModel):
    """Overall schedule health status"""
    total_schedules: int
    active_schedules: int
    paused_schedules: int
    disabled_schedules: int
    schedules_with_recent_failures: int
    upcoming_runs_24h: int
    total_backups_created: int

# ============================================================================
# Cron Helper Models
# ============================================================================

class CronPreset(BaseModel):
    """Predefined cron expressions"""
    name: str
    description: str
    cron_expression: str
    frequency: ScheduleFrequency

# Predefined cron presets
CRON_PRESETS = [
    CronPreset(
        name="Every Hour",
        description="Run at the start of every hour",
        cron_expression="0 * * * *",
        frequency=ScheduleFrequency.HOURLY
    ),
    CronPreset(
        name="Daily at Midnight",
        description="Run every day at 00:00 UTC",
        cron_expression="0 0 * * *",
        frequency=ScheduleFrequency.DAILY
    ),
    CronPreset(
        name="Daily at 2 AM",
        description="Run every day at 02:00 UTC",
        cron_expression="0 2 * * *",
        frequency=ScheduleFrequency.DAILY
    ),
    CronPreset(
        name="Weekly on Sunday",
        description="Run every Sunday at 00:00 UTC",
        cron_expression="0 0 * * 0",
        frequency=ScheduleFrequency.WEEKLY
    ),
    CronPreset(
        name="Monthly on 1st",
        description="Run on the 1st of every month at 00:00 UTC",
        cron_expression="0 0 1 * *",
        frequency=ScheduleFrequency.MONTHLY
    ),
    CronPreset(
        name="Twice Daily",
        description="Run at 00:00 and 12:00 UTC",
        cron_expression="0 0,12 * * *",
        frequency=ScheduleFrequency.CUSTOM
    ),
    CronPreset(
        name="Weekdays at 9 AM",
        description="Run Monday-Friday at 09:00 UTC",
        cron_expression="0 9 * * 1-5",
        frequency=ScheduleFrequency.CUSTOM
    )
]

class CronPresetsResponse(BaseModel):
    """List of cron presets"""
    presets: List[CronPreset]

# ============================================================================
# Retention Policy Models
# ============================================================================

class RetentionPolicyResult(BaseModel):
    """Result of retention policy application"""
    deleted_backups: List[str]
    deleted_count: int
    freed_space_bytes: int
    reason: str  # "age" or "count"