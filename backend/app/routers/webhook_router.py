"""
Webhook Router
Manages webhook endpoints
"""

from fastapi import APIRouter, HTTPException, Depends, status
from app.models.webhook_models import (
    WebhookCreate,
    WebhookResponse,
    WebhookList,
    WebhookTestResponse
)
from app.services.webhook_service import WebhookService
from app.middleware.auth_middleware import verify_api_key
from app.database import get_database
from app.services.quota_manager import check_api_calls_quota, increment_api_calls

router = APIRouter()

@router.post("/webhooks", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    webhook_data: WebhookCreate,
    current_user: dict = Depends(verify_api_key)
):
    """
    Create a new webhook
    
    Webhooks allow you to receive real-time notifications when events occur.
    
    Supported events:
    - data.created: Triggered when data is created
    - data.updated: Triggered when data is updated
    - data.deleted: Triggered when data is deleted
    - file.uploaded: Triggered when a file is uploaded
    
    The webhook URL will receive POST requests with:
    - X-Webhook-Signature: HMAC signature for verification
    - X-Webhook-Event: Event name
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        webhook_service = WebhookService(db)
        
        # Create webhook
        webhook = await webhook_service.create_webhook(
            user_id=str(current_user["_id"]),
            url=webhook_data.url,
            events=webhook_data.events,
            description=webhook_data.description
        )
        
        await increment_api_calls(current_user["_id"])
        
        return WebhookResponse(
            id=str(webhook["_id"]),
            url=webhook["url"],
            events=webhook["events"],
            secret=webhook["secret"],
            is_active=webhook["is_active"],
            description=webhook.get("description"),
            created_at=webhook["created_at"].isoformat(),
            last_triggered=webhook["last_triggered"].isoformat() if webhook.get("last_triggered") else None,
            success_count=webhook.get("success_count", 0),
            failure_count=webhook.get("failure_count", 0)
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create webhook: {str(e)}"
        )

@router.get("/webhooks", response_model=WebhookList)
async def list_webhooks(
    current_user: dict = Depends(verify_api_key)
):
    """
    List all webhooks
    
    Returns all webhooks configured for the authenticated user.
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        webhook_service = WebhookService(db)
        
        # Get webhooks
        webhooks = await webhook_service.get_webhooks(str(current_user["_id"]))
        
        await increment_api_calls(current_user["_id"])
        
        # Format response
        webhook_list = []
        for webhook in webhooks:
            webhook_list.append(WebhookResponse(
                id=str(webhook["_id"]),
                url=webhook["url"],
                events=webhook["events"],
                secret=webhook["secret"],
                is_active=webhook["is_active"],
                description=webhook.get("description"),
                created_at=webhook["created_at"].isoformat(),
                last_triggered=webhook["last_triggered"].isoformat() if webhook.get("last_triggered") else None,
                success_count=webhook.get("success_count", 0),
                failure_count=webhook.get("failure_count", 0)
            ))
        
        return WebhookList(
            success=True,
            webhooks=webhook_list,
            total=len(webhook_list)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list webhooks: {str(e)}"
        )

@router.delete("/webhooks/{webhook_id}")
async def delete_webhook(
    webhook_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Delete a webhook
    
    Permanently deletes a webhook. This action cannot be undone.
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        webhook_service = WebhookService(db)
        
        # Delete webhook
        success = await webhook_service.delete_webhook(
            webhook_id=webhook_id,
            user_id=str(current_user["_id"])
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        await increment_api_calls(current_user["_id"])
        
        return {
            "success": True,
            "message": "Webhook deleted successfully",
            "id": webhook_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete webhook: {str(e)}"
        )

@router.post("/webhooks/{webhook_id}/test", response_model=WebhookTestResponse)
async def test_webhook(
    webhook_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Test a webhook
    
    Sends a test event to the webhook URL to verify it's working correctly.
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        webhook_service = WebhookService(db)
        
        # Test webhook
        result = await webhook_service.test_webhook(
            webhook_id=webhook_id,
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        return WebhookTestResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test webhook: {str(e)}"
        )

@router.get("/webhooks/{webhook_id}/logs")
async def get_webhook_logs(
    webhook_id: str,
    limit: int = 20,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get webhook delivery logs
    
    Returns recent delivery attempts for a webhook.
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        from bson import ObjectId
        
        db = await get_database()
        
        # Verify webhook belongs to user
        webhook = await db.webhooks.find_one({
            "_id": ObjectId(webhook_id),
            "user_id": str(current_user["_id"])
        })
        
        if not webhook:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Webhook not found"
            )
        
        # Get logs
        cursor = db.webhook_logs.find(
            {"webhook_id": ObjectId(webhook_id)}
        ).sort("created_at", -1).limit(limit)
        
        logs = await cursor.to_list(length=limit)
        
        await increment_api_calls(current_user["_id"])
        
        # Format response
        formatted_logs = []
        for log in logs:
            formatted_logs.append({
                "id": str(log["_id"]),
                "event": log["event"],
                "status_code": log["status_code"],
                "response_time_ms": log.get("response_time_ms", 0),
                "success": log["success"],
                "error": log.get("error"),
                "created_at": log["created_at"].isoformat()
            })
        
        return {
            "success": True,
            "logs": formatted_logs,
            "total": len(formatted_logs)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get webhook logs: {str(e)}"
        )