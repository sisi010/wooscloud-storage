"""
Backup Router
API endpoints for backup and restore operations
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import List, Optional

from app.models.backup_models import (
    BackupCreateRequest,
    BackupMetadata,
    BackupListResponse,
    RestoreRequest,
    RestoreJobMetadata,
    BackupStatsResponse
)
from app.middleware.auth_middleware import verify_api_key
from app.database import get_database
from app.services.backup_service import BackupService
from app.services.quota_manager import check_api_calls_quota, increment_api_calls

router = APIRouter()

# ============================================================================
# CREATE BACKUP
# ============================================================================

@router.post("/backups", response_model=BackupMetadata, status_code=status.HTTP_201_CREATED)
async def create_backup(
    request: BackupCreateRequest,
    current_user: dict = Depends(verify_api_key)
):
    """
    Create a new backup
    
    Features:
    - Full or incremental backup
    - Select specific collections or all
    - Include/exclude files
    - Compression support
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        backup_service = BackupService(db)
        
        backup = await backup_service.create_backup(
            user_id=str(current_user["_id"]),
            request=request
        )
        
        await increment_api_calls(current_user["_id"])
        
        return backup
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create backup: {str(e)}"
        )


# ============================================================================
# LIST BACKUPS
# ============================================================================

@router.get("/backups", response_model=BackupListResponse)
async def list_backups(
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(verify_api_key)
):
    """
    List all backups for the user
    
    Returns:
    - Paginated list of backups
    - Sorted by creation date (newest first)
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        backup_service = BackupService(db)
        
        backups = await backup_service.list_backups(
            user_id=str(current_user["_id"]),
            limit=limit,
            skip=skip
        )
        
        # Get total count
        total = await db.backups.count_documents({
            "user_id": str(current_user["_id"])
        })
        
        await increment_api_calls(current_user["_id"])
        
        return BackupListResponse(
            backups=backups,
            total=total,
            page=skip // limit + 1,
            page_size=limit
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list backups: {str(e)}"
        )


# ============================================================================
# GET BACKUP
# ============================================================================

@router.get("/backups/{backup_id}", response_model=BackupMetadata)
async def get_backup(
    backup_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get backup details by ID
    
    Returns:
    - Complete backup metadata
    - Status, size, record count, etc.
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        backup_service = BackupService(db)
        
        backup = await backup_service.get_backup(
            backup_id=backup_id,
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        if not backup:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backup {backup_id} not found"
            )
        
        return backup
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get backup: {str(e)}"
        )


# ============================================================================
# DELETE BACKUP
# ============================================================================

@router.delete("/backups/{backup_id}")
async def delete_backup(
    backup_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Delete a backup
    
    WARNING: This action cannot be undone!
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        backup_service = BackupService(db)
        
        deleted = await backup_service.delete_backup(
            backup_id=backup_id,
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backup {backup_id} not found"
            )
        
        return {"message": "Backup deleted successfully", "backup_id": backup_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete backup: {str(e)}"
        )


# ============================================================================
# RESTORE BACKUP
# ============================================================================

@router.post("/backups/restore", response_model=RestoreJobMetadata, status_code=status.HTTP_201_CREATED)
async def restore_backup(
    request: RestoreRequest,
    current_user: dict = Depends(verify_api_key)
):
    """
    Restore from a backup
    
    Features:
    - Restore all or specific collections
    - Conflict resolution (skip/overwrite/rename)
    - Dry run mode (preview without applying)
    - Point-in-time recovery (if timestamp provided)
    
    WARNING: Overwrite mode will replace existing data!
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        backup_service = BackupService(db)
        
        restore_job = await backup_service.restore_backup(
            user_id=str(current_user["_id"]),
            request=request
        )
        
        await increment_api_calls(current_user["_id"])
        
        return restore_job
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to restore backup: {str(e)}"
        )


# ============================================================================
# GET RESTORE JOB
# ============================================================================

@router.get("/restore-jobs/{job_id}", response_model=RestoreJobMetadata)
async def get_restore_job(
    job_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get restore job status
    
    Returns:
    - Job status (pending/in_progress/completed/failed)
    - Records restored count
    - Conflicts encountered and resolved
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        
        job = await db.restore_jobs.find_one({
            "_id": job_id,
            "user_id": str(current_user["_id"])
        })
        
        await increment_api_calls(current_user["_id"])
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Restore job {job_id} not found"
            )
        
        backup_service = BackupService(db)
        return backup_service._doc_to_restore_job(job)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get restore job: {str(e)}"
        )


# ============================================================================
# BACKUP STATISTICS
# ============================================================================

@router.get("/backups/stats/summary", response_model=BackupStatsResponse)
async def get_backup_stats(
    current_user: dict = Depends(verify_api_key)
):
    """
    Get backup statistics
    
    Returns:
    - Total backups count
    - Total size
    - Latest and oldest backups
    - Breakdown by type and status
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        user_id = str(current_user["_id"])
        
        # Get all backups
        backups = await db.backups.find({"user_id": user_id}).to_list(None)
        
        # Calculate stats
        total_backups = len(backups)
        total_size = sum(b.get("size_bytes", 0) for b in backups)
        
        # Latest and oldest
        latest = None
        oldest = None
        if backups:
            sorted_backups = sorted(backups, key=lambda x: x["created_at"], reverse=True)
            backup_service = BackupService(db)
            latest = backup_service._doc_to_metadata(sorted_backups[0])
            oldest = backup_service._doc_to_metadata(sorted_backups[-1])
        
        # By type
        by_type = {}
        for b in backups:
            backup_type = b["backup_type"]
            by_type[backup_type] = by_type.get(backup_type, 0) + 1
        
        # By status
        by_status = {}
        for b in backups:
            backup_status = b["status"]
            by_status[backup_status] = by_status.get(backup_status, 0) + 1
        
        await increment_api_calls(current_user["_id"])
        
        return BackupStatsResponse(
            total_backups=total_backups,
            total_size_bytes=total_size,
            latest_backup=latest,
            oldest_backup=oldest,
            by_type=by_type,
            by_status=by_status
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get backup stats: {str(e)}"
        )


# ============================================================================
# DOWNLOAD BACKUP (Future enhancement)
# ============================================================================

@router.get("/backups/{backup_id}/download")
async def download_backup(
    backup_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Download backup file
    
    Note: This is a placeholder for future implementation
    In production, this would generate a signed URL to download
    the backup from cloud storage (R2, S3, etc.)
    """
    
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Download feature coming soon. Backups are stored in database."
    )