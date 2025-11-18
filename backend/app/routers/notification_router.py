"""
Notification Router
API endpoints for notification management
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query
from typing import Optional

from app.models.notification_models import (
    NotificationCreate, Notification, NotificationListResponse,
    NotificationPreferences, NotificationPreferencesUpdate,
    NotificationStats, NotificationEventType, NotificationPriority,
    NOTIFICATION_TEMPLATES
)
from app.middleware.auth_middleware import verify_api_key
from app.database import get_database
from app.services.notification_service import NotificationService
from app.services.quota_manager import check_api_calls_quota, increment_api_calls

router = APIRouter()

@router.get("/notifications/templates")
async def get_notification_templates(
    current_user: dict = Depends(verify_api_key)
):
    """
    Get available notification templates
    """
    
    await check_api_calls_quota(current_user["_id"])
    await increment_api_calls(current_user["_id"])
    
    templates_list = [
        {
            "event_type": template.event_type.value,
            "title_template": template.title_template,
            "message_template": template.message_template,
            "default_priority": template.default_priority.value,
            "variables": template.variables
        }
        for template in NOTIFICATION_TEMPLATES.values()
    ]
    
    return {"templates": templates_list}

# ============================================================================
# NOTIFICATIONS
# ============================================================================

@router.post("/notifications", response_model=Notification, status_code=status.HTTP_201_CREATED)
async def create_notification(
    request: NotificationCreate,
    current_user: dict = Depends(verify_api_key)
):
    """
    Create a notification
    
    Note: Notifications are usually created automatically by system events.
    This endpoint is for manual/custom notifications.
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        notif_service = NotificationService(db)
        
        notification = await notif_service.create_notification(
            user_id=str(current_user["_id"]),
            request=request
        )
        
        await increment_api_calls(current_user["_id"])
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Notification not created (user preferences or quiet hours)"
            )
        
        return notification
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create notification: {str(e)}"
        )


@router.get("/notifications", response_model=NotificationListResponse)
async def list_notifications(
    unread_only: bool = Query(False, description="Show only unread notifications"),
    event_type: Optional[NotificationEventType] = None,
    priority: Optional[NotificationPriority] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: dict = Depends(verify_api_key)
):
    """
    List notifications
    
    Filters:
    - unread_only: Show only unread notifications
    - event_type: Filter by event type
    - priority: Filter by priority
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        notif_service = NotificationService(db)
        
        notifications, total, unread_count = await notif_service.list_notifications(
            user_id=str(current_user["_id"]),
            unread_only=unread_only,
            event_type=event_type,
            priority=priority,
            page=page,
            page_size=page_size
        )
        
        await increment_api_calls(current_user["_id"])
        
        return NotificationListResponse(
            notifications=notifications,
            total=total,
            unread_count=unread_count,
            page=page,
            page_size=page_size
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list notifications: {str(e)}"
        )


@router.get("/notifications/{notification_id}", response_model=Notification)
async def get_notification(
    notification_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get notification by ID
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        notif_service = NotificationService(db)
        
        notification = await notif_service.get_notification(
            notif_id=notification_id,
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        if not notification:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notification {notification_id} not found"
            )
        
        return notification
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get notification: {str(e)}"
        )


@router.post("/notifications/{notification_id}/read")
async def mark_notification_as_read(
    notification_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Mark notification as read
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        notif_service = NotificationService(db)
        
        marked = await notif_service.mark_as_read(
            notif_id=notification_id,
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        if not marked:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found or already read"
            )
        
        return {"message": "Notification marked as read", "notification_id": notification_id}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark notification: {str(e)}"
        )


@router.post("/notifications/read-all")
async def mark_all_as_read(
    current_user: dict = Depends(verify_api_key)
):
    """
    Mark all notifications as read
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        notif_service = NotificationService(db)
        
        count = await notif_service.mark_all_as_read(
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        return {
            "message": f"Marked {count} notifications as read",
            "count": count
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to mark all as read: {str(e)}"
        )


@router.delete("/notifications/{notification_id}")
async def delete_notification(
    notification_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Delete notification
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        notif_service = NotificationService(db)
        
        deleted = await notif_service.delete_notification(
            notif_id=notification_id,
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Notification {notification_id} not found"
            )
        
        return {
            "message": "Notification deleted successfully",
            "notification_id": notification_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete notification: {str(e)}"
        )


# ============================================================================
# PREFERENCES
# ============================================================================

@router.get("/notifications/preferences/me", response_model=NotificationPreferences)
async def get_my_preferences(
    current_user: dict = Depends(verify_api_key)
):
    """
    Get my notification preferences
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        notif_service = NotificationService(db)
        
        preferences = await notif_service.get_preferences(
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        return preferences
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get preferences: {str(e)}"
        )


@router.patch("/notifications/preferences/me", response_model=NotificationPreferences)
async def update_my_preferences(
    request: NotificationPreferencesUpdate,
    current_user: dict = Depends(verify_api_key)
):
    """
    Update my notification preferences
    
    You can configure:
    - Enabled channels (email, webhook, in-app)
    - Subscribed events
    - Minimum priority
    - Quiet hours
    - Daily digest
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        notif_service = NotificationService(db)
        
        preferences = await notif_service.update_preferences(
            user_id=str(current_user["_id"]),
            request=request
        )
        
        await increment_api_calls(current_user["_id"])
        
        return preferences
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update preferences: {str(e)}"
        )


# ============================================================================
# STATISTICS
# ============================================================================

@router.get("/notifications/stats/me", response_model=NotificationStats)
async def get_my_notification_stats(
    current_user: dict = Depends(verify_api_key)
):
    """
    Get my notification statistics
    
    Returns:
    - Total sent, delivered, failed, read, unread
    - Breakdown by channel, priority, event type
    - Delivery and read rates
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        notif_service = NotificationService(db)
        
        stats = await notif_service.get_statistics(
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        return stats
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )


