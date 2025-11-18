"""
Mobile SDK API Router
API endpoints optimized for mobile clients (iOS/Android)
"""

from fastapi import APIRouter, HTTPException, Depends, Header, status
from typing import Optional
from datetime import datetime
from bson import ObjectId

from app.middleware.auth_middleware import verify_api_key
from app.database import get_database

router = APIRouter(prefix="/mobile", tags=["Mobile SDK"])


@router.get("/sdk-info")
async def get_sdk_info():
    """
    Get Mobile SDK information
    
    Returns SDK versions, documentation, and download links
    """
    
    return {
        "success": True,
        "sdk": {
            "ios": {
                "version": "1.0.0",
                "min_ios_version": "14.0",
                "swift_version": "5.5",
                "cocoapods": "pod 'WoosCloudSDK', '~> 1.0'",
                "spm": "https://github.com/wooscloud/ios-sdk",
                "documentation": "https://docs.wooscloud.com/ios"
            },
            "android": {
                "version": "1.0.0",
                "min_sdk": 24,
                "kotlin_version": "1.8.0",
                "gradle": "implementation 'com.wooscloud:sdk:1.0.0'",
                "maven": "https://maven.wooscloud.com/android-sdk",
                "documentation": "https://docs.wooscloud.com/android"
            },
            "features": [
                "File upload/download",
                "Background uploads",
                "Offline sync",
                "Push notifications",
                "Photo library integration",
                "Document picker",
                "Biometric authentication"
            ]
        }
    }


@router.post("/register-device")
async def register_device(
    device_token: str = Header(...),
    platform: str = Header(..., description="ios or android"),
    app_version: str = Header(...),
    current_user: dict = Depends(verify_api_key)
):
    """
    Register mobile device for push notifications
    """
    
    db = await get_database()
    
    # Register or update device
    device_doc = {
        "user_id": str(current_user["_id"]),
        "device_token": device_token,
        "platform": platform,
        "app_version": app_version,
        "registered_at": datetime.utcnow(),
        "last_active": datetime.utcnow(),
        "enabled": True
    }
    
    await db.mobile_devices.update_one(
        {
            "user_id": str(current_user["_id"]),
            "device_token": device_token
        },
        {"$set": device_doc},
        upsert=True
    )
    
    return {
        "success": True,
        "message": "Device registered successfully",
        "push_enabled": True
    }


@router.post("/sync")
async def sync_mobile(
    last_sync: Optional[str] = Header(None),
    current_user: dict = Depends(verify_api_key)
):
    """
    Sync data for mobile client
    
    Returns changes since last sync
    """
    
    db = await get_database()
    
    # Parse last sync time
    if last_sync:
        try:
            last_sync_time = datetime.fromisoformat(last_sync)
        except:
            last_sync_time = datetime.utcnow() - timedelta(days=7)
    else:
        last_sync_time = datetime.utcnow() - timedelta(days=7)
    
    # Get changes since last sync
    changes = await db.storage_data.find({
        "user_id": str(current_user["_id"]),
        "$or": [
            {"created_at": {"$gte": last_sync_time}},
            {"updated_at": {"$gte": last_sync_time}}
        ]
    }).limit(100).to_list(None)
    
    # Get deleted items
    deleted = await db.deleted_items.find({
        "user_id": str(current_user["_id"]),
        "deleted_at": {"$gte": last_sync_time}
    }).to_list(None)
    
    return {
        "success": True,
        "sync_time": datetime.utcnow().isoformat(),
        "changes": {
            "added": len([c for c in changes if c.get("created_at", datetime.min) >= last_sync_time]),
            "modified": len([c for c in changes if c.get("updated_at", datetime.min) >= last_sync_time]),
            "deleted": len(deleted)
        },
        "data": [
            {
                "id": str(doc["_id"]),
                "collection": doc.get("collection"),
                "data": doc.get("data"),
                "updated_at": doc.get("updated_at", doc.get("created_at")).isoformat()
            }
            for doc in changes
        ],
        "deleted_ids": [str(doc["data_id"]) for doc in deleted]
    }


@router.get("/offline-queue")
async def get_offline_queue(
    current_user: dict = Depends(verify_api_key)
):
    """
    Get offline queue status
    """
    
    db = await get_database()
    
    queue = await db.offline_queue.find({
        "user_id": str(current_user["_id"]),
        "status": "pending"
    }).to_list(None)
    
    return {
        "success": True,
        "queue": {
            "pending": len(queue),
            "items": [
                {
                    "id": str(item["_id"]),
                    "action": item["action"],
                    "created_at": item["created_at"].isoformat()
                }
                for item in queue
            ]
        }
    }


@router.get("/bandwidth-usage")
async def get_bandwidth_usage(
    current_user: dict = Depends(verify_api_key)
):
    """
    Get bandwidth usage for mobile optimization
    """
    
    db = await get_database()
    
    # Get device bandwidth usage
    usage = await db.mobile_bandwidth.find({
        "user_id": str(current_user["_id"])
    }).sort("date", -1).limit(30).to_list(None)
    
    total_upload = sum(u.get("upload_bytes", 0) for u in usage)
    total_download = sum(u.get("download_bytes", 0) for u in usage)
    
    return {
        "success": True,
        "bandwidth": {
            "total_upload_mb": round(total_upload / (1024**2), 2),
            "total_download_mb": round(total_download / (1024**2), 2),
            "daily_average_mb": round((total_upload + total_download) / (1024**2) / max(len(usage), 1), 2)
        },
        "recommendation": "Consider using WiFi for large uploads" if total_upload > 100*1024*1024 else "Bandwidth usage is optimal"
    }


from datetime import timedelta

@router.post("/feedback")
async def submit_mobile_feedback(
    rating: int,
    comment: Optional[str] = None,
    platform: str = Header(...),
    app_version: str = Header(...),
    current_user: dict = Depends(verify_api_key)
):
    """
    Submit mobile app feedback
    """
    
    db = await get_database()
    
    feedback_doc = {
        "user_id": str(current_user["_id"]),
        "platform": platform,
        "app_version": app_version,
        "rating": rating,
        "comment": comment,
        "submitted_at": datetime.utcnow()
    }
    
    await db.mobile_feedback.insert_one(feedback_doc)
    
    return {
        "success": True,
        "message": "Thank you for your feedback!",
        "rating": rating
    }