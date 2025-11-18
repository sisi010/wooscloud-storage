"""
Audit Log Router
API endpoints for audit logs, statistics, and security monitoring
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query, Request
from typing import Optional
from datetime import datetime, timedelta

from app.models.audit_models import (
    AuditLogListResponse, AuditLogFilter, AuditStatsResponse,
    SecurityEventListResponse, SystemHealthMetrics,
    AuditEventType, AuditSeverity, AuditStatus
)
from app.middleware.auth_middleware import verify_api_key
from app.database import get_database
from app.services.audit_service import AuditLogService
from app.services.quota_manager import check_api_calls_quota, increment_api_calls

router = APIRouter()

# ============================================================================
# AUDIT LOGS
# ============================================================================

@router.get("/audit/logs", response_model=AuditLogListResponse)
async def get_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    user_id: Optional[str] = None,
    event_type: Optional[AuditEventType] = None,
    severity: Optional[AuditSeverity] = None,
    status: Optional[AuditStatus] = None,
    resource_type: Optional[str] = None,
    collection: Optional[str] = None,
    organization_id: Optional[str] = None,
    team_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    ip_address: Optional[str] = None,
    search: Optional[str] = None,
    sort_by: str = Query("timestamp", pattern="^(timestamp|event_type|severity|status)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Get audit logs with advanced filtering
    
    Features:
    - Filter by user, event type, severity, status
    - Date range filtering
    - Text search
    - Pagination and sorting
    
    Note: Only owners and admins can view all logs.
    Regular users can only view their own logs.
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        audit_service = AuditLogService(db)
        
        # Create filters
        filters = AuditLogFilter(
            user_id=user_id,
            event_type=event_type,
            severity=severity,
            status=status,
            resource_type=resource_type,
            collection=collection,
            organization_id=organization_id,
            team_id=team_id,
            start_date=start_date,
            end_date=end_date,
            ip_address=ip_address,
            search=search
        )
        
        # Get logs
        logs, total = await audit_service.get_logs(
            filters=filters,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        await increment_api_calls(current_user["_id"])
        
        return AuditLogListResponse(
            logs=logs,
            total=total,
            page=page,
            page_size=page_size,
            filters=filters.dict(exclude_none=True)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit logs: {str(e)}"
        )


@router.get("/audit/logs/{log_id}")
async def get_audit_log(
    log_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get single audit log by ID
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        audit_service = AuditLogService(db)
        
        log = await audit_service.get_log_by_id(log_id)
        
        await increment_api_calls(current_user["_id"])
        
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Audit log {log_id} not found"
            )
        
        return log
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get audit log: {str(e)}"
        )


# ============================================================================
# STATISTICS
# ============================================================================

@router.get("/audit/stats", response_model=AuditStatsResponse)
async def get_audit_statistics(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    user_id: Optional[str] = None,
    organization_id: Optional[str] = None,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get audit log statistics
    
    Returns:
    - Total events count
    - Breakdown by event type, severity, status
    - Top users
    - Unique users and IPs
    
    Default: Last 30 days
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        audit_service = AuditLogService(db)
        
        # Parse dates
        start = datetime.fromisoformat(start_date) if start_date else None
        end = datetime.fromisoformat(end_date) if end_date else None
        
        stats = await audit_service.get_statistics(
            start_date=start,
            end_date=end,
            user_id=user_id,
            organization_id=organization_id
        )
        
        await increment_api_calls(current_user["_id"])
        
        return stats
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


# ============================================================================
# SECURITY EVENTS
# ============================================================================

@router.get("/audit/security-events", response_model=SecurityEventListResponse)
async def get_security_events(
    resolved: Optional[bool] = None,
    severity: Optional[AuditSeverity] = None,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get security events
    
    Security events include:
    - Failed authentication attempts
    - Rate limit violations
    - Unauthorized access attempts
    - Critical system errors
    
    Requires: Admin or Owner role
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        audit_service = AuditLogService(db)
        
        events = await audit_service.get_security_events(
            resolved=resolved,
            severity=severity
        )
        
        await increment_api_calls(current_user["_id"])
        
        # Count unresolved
        unresolved = sum(1 for e in events if not e.resolved)
        
        return SecurityEventListResponse(
            events=events,
            total=len(events),
            unresolved_count=unresolved
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get security events: {str(e)}"
        )


# ============================================================================
# SYSTEM HEALTH
# ============================================================================

@router.get("/audit/health", response_model=SystemHealthMetrics)
async def get_system_health(
    current_user: dict = Depends(verify_api_key)
):
    """
    Get real-time system health metrics
    
    Returns metrics for the last hour:
    - Total requests
    - Success rate
    - Average response time
    - Error rate
    - Active users
    - Rate limit hits
    - Security events
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        audit_service = AuditLogService(db)
        
        health = await audit_service.get_system_health()
        
        await increment_api_calls(current_user["_id"])
        
        return health
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get system health: {str(e)}"
        )


# ============================================================================
# USER ACTIVITY
# ============================================================================

@router.get("/audit/my-activity")
async def get_my_activity(
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(verify_api_key)
):
    """
    Get current user's activity summary
    
    Returns:
    - Recent activity timeline
    - Most common actions
    - Collections accessed
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        audit_service = AuditLogService(db)
        
        start_date = datetime.utcnow() - timedelta(days=days)
        
        filters = AuditLogFilter(
            user_id=str(current_user["_id"]),
            start_date=start_date.isoformat()
        )
        
        logs, total = await audit_service.get_logs(
            filters=filters,
            page=1,
            page_size=100
        )
        
        # Calculate summary
        event_counts = {}
        collections = set()
        
        for log in logs:
            event_counts[log.event_type.value] = event_counts.get(log.event_type.value, 0) + 1
            if log.collection:
                collections.add(log.collection)
        
        # Sort by count
        most_common = sorted(
            [{"action": k, "count": v} for k, v in event_counts.items()],
            key=lambda x: x["count"],
            reverse=True
        )[:10]
        
        await increment_api_calls(current_user["_id"])
        
        return {
            "total_actions": total,
            "date_range": {
                "start": start_date.isoformat(),
                "end": datetime.utcnow().isoformat()
            },
            "most_common_actions": most_common,
            "collections_accessed": list(collections),
            "recent_activity": [
                {
                    "timestamp": log.timestamp,
                    "event_type": log.event_type.value,
                    "endpoint": log.endpoint,
                    "status": log.status.value
                }
                for log in logs[:20]
            ]
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user activity: {str(e)}"
        )