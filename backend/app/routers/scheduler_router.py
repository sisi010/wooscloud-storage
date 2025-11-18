"""
Backup Scheduler Router
API endpoints for backup schedule management
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Optional

from app.models.schedule_models import (
    BackupScheduleCreate, BackupScheduleUpdate,
    BackupSchedule, BackupScheduleListResponse,
    BackupJob, BackupJobListResponse,
    ScheduleStatistics, ScheduleHealthStatus,
    CronPresetsResponse, CRON_PRESETS,
    ScheduleStatus, BackupJobStatus
)
from app.middleware.auth_middleware import verify_api_key
from app.database import get_database
from app.services.scheduler_service import BackupSchedulerService
from app.services.quota_manager import check_api_calls_quota, increment_api_calls

router = APIRouter()

# ============================================================================
# SCHEDULES
# ============================================================================

@router.post("/backup-schedules", response_model=BackupSchedule, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    request: BackupScheduleCreate,
    current_user: dict = Depends(verify_api_key)
):
    """
    Create a new backup schedule
    
    Schedule frequencies:
    - HOURLY: Every hour
    - DAILY: Every day at 2 AM UTC
    - WEEKLY: Every Sunday at 2 AM UTC
    - MONTHLY: 1st of month at 2 AM UTC
    - CUSTOM: Use cron expression
    
    Retention policies:
    - retention_days: Delete backups older than X days
    - max_backups: Keep only X most recent backups
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        scheduler = BackupSchedulerService(db)
        
        schedule = await scheduler.create_schedule(
            user_id=str(current_user["_id"]),
            request=request
        )
        
        await increment_api_calls(current_user["_id"])
        
        return schedule
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create schedule: {str(e)}"
        )


@router.get("/backup-schedules", response_model=BackupScheduleListResponse)
async def list_schedules(
    status_filter: Optional[ScheduleStatus] = Query(None, alias="status"),
    current_user: dict = Depends(verify_api_key)
):
    """
    List all backup schedules
    
    Filter by status: active, paused, disabled
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        scheduler = BackupSchedulerService(db)
        
        schedules = await scheduler.list_schedules(
            user_id=str(current_user["_id"]),
            status=status_filter
        )
        
        await increment_api_calls(current_user["_id"])
        
        return BackupScheduleListResponse(
            schedules=schedules,
            total=len(schedules)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list schedules: {str(e)}"
        )


@router.get("/backup-schedules/{schedule_id}", response_model=BackupSchedule)
async def get_schedule(
    schedule_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get schedule details
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        scheduler = BackupSchedulerService(db)
        
        schedule = await scheduler.get_schedule(
            schedule_id=schedule_id,
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule {schedule_id} not found"
            )
        
        return schedule
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get schedule: {str(e)}"
        )


@router.patch("/backup-schedules/{schedule_id}", response_model=BackupSchedule)
async def update_schedule(
    schedule_id: str,
    request: BackupScheduleUpdate,
    current_user: dict = Depends(verify_api_key)
):
    """
    Update backup schedule
    
    You can update:
    - Schedule settings (frequency, cron, timezone)
    - Backup configuration
    - Retention policy
    - Status (active/paused/disabled)
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        scheduler = BackupSchedulerService(db)
        
        schedule = await scheduler.update_schedule(
            schedule_id=schedule_id,
            user_id=str(current_user["_id"]),
            request=request
        )
        
        await increment_api_calls(current_user["_id"])
        
        return schedule
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update schedule: {str(e)}"
        )


@router.delete("/backup-schedules/{schedule_id}")
async def delete_schedule(
    schedule_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Delete backup schedule
    
    This will also delete all associated job records.
    Existing backups will NOT be deleted.
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        scheduler = BackupSchedulerService(db)
        
        deleted = await scheduler.delete_schedule(
            schedule_id=schedule_id,
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Schedule {schedule_id} not found"
            )
        
        return {
            "message": "Schedule deleted successfully",
            "schedule_id": schedule_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete schedule: {str(e)}"
        )


# ============================================================================
# MANUAL EXECUTION
# ============================================================================

@router.post("/backup-schedules/{schedule_id}/execute", response_model=BackupJob)
async def execute_schedule_now(
    schedule_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Manually execute a schedule now
    
    This will create a backup immediately,
    regardless of the schedule.
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        scheduler = BackupSchedulerService(db)
        
        # Verify ownership
        schedule = await scheduler.get_schedule(schedule_id, str(current_user["_id"]))
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found"
            )
        
        job = await scheduler.execute_schedule(schedule_id)
        
        await increment_api_calls(current_user["_id"])
        
        return job
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to execute schedule: {str(e)}"
        )


# ============================================================================
# JOB HISTORY
# ============================================================================

@router.get("/backup-schedules/{schedule_id}/jobs", response_model=BackupJobListResponse)
async def list_schedule_jobs(
    schedule_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(verify_api_key)
):
    """
    List execution history for a schedule
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        
        # Verify ownership
        scheduler = BackupSchedulerService(db)
        schedule = await scheduler.get_schedule(schedule_id, str(current_user["_id"]))
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found"
            )
        
        # Get jobs
        skip = (page - 1) * page_size
        jobs = await db.backup_jobs.find({
            "schedule_id": schedule_id
        }).sort("started_at", -1).skip(skip).limit(page_size).to_list(None)
        
        total = await db.backup_jobs.count_documents({"schedule_id": schedule_id})
        
        await increment_api_calls(current_user["_id"])
        
        return BackupJobListResponse(
            jobs=[scheduler._doc_to_job(j) for j in jobs],
            total=total,
            page=page,
            page_size=page_size
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {str(e)}"
        )


# ============================================================================
# STATISTICS
# ============================================================================

@router.get("/backup-schedules/{schedule_id}/stats", response_model=ScheduleStatistics)
async def get_schedule_statistics(
    schedule_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get schedule execution statistics
    
    Returns:
    - Total runs, success/failure counts
    - Success rate
    - Average duration
    - Recent activity
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        scheduler = BackupSchedulerService(db)
        
        stats = await scheduler.get_schedule_statistics(
            schedule_id=schedule_id,
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        return stats
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


# ============================================================================
# CRON HELPERS
# ============================================================================

@router.get("/backup-schedules/cron/presets", response_model=CronPresetsResponse)
async def get_cron_presets(
    current_user: dict = Depends(verify_api_key)
):
    """
    Get predefined cron expressions
    
    Useful for building schedule UI
    """
    
    await check_api_calls_quota(current_user["_id"])
    await increment_api_calls(current_user["_id"])
    
    return CronPresetsResponse(presets=CRON_PRESETS)