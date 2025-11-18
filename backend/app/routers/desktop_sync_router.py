"""
Desktop Sync Client API Router
API endpoints for desktop synchronization clients (Windows/Mac/Linux)
Similar to Dropbox/Google Drive desktop clients
"""

from fastapi import APIRouter, HTTPException, Depends, Header, Query, status
from typing import Optional, List
from datetime import datetime, timedelta
from bson import ObjectId
from pydantic import BaseModel

from app.middleware.auth_middleware import verify_api_key
from app.database import get_database

router = APIRouter(prefix="/desktop-sync", tags=["Desktop Sync"])


class SyncFolder(BaseModel):
    """Sync folder configuration"""
    path: str
    name: str
    sync_mode: str = "two-way"  # one-way-upload, one-way-download, two-way
    excluded_patterns: List[str] = []


@router.get("/client-info")
async def get_client_info():
    """
    Get desktop client information
    
    Returns client versions and download links
    """
    
    return {
        "success": True,
        "clients": {
            "windows": {
                "version": "1.0.0",
                "min_version": "Windows 10",
                "download": "https://download.wooscloud.com/WoosCloud-Windows-1.0.0.exe",
                "size_mb": 45.2,
                "checksum": "sha256:abc123..."
            },
            "macos": {
                "version": "1.0.0",
                "min_version": "macOS 11.0",
                "download": "https://download.wooscloud.com/WoosCloud-Mac-1.0.0.dmg",
                "size_mb": 38.7,
                "checksum": "sha256:def456..."
            },
            "linux": {
                "version": "1.0.0",
                "formats": ["deb", "rpm", "AppImage"],
                "download": "https://download.wooscloud.com/linux/",
                "size_mb": 42.1
            }
        },
        "features": [
            "Real-time sync",
            "Selective sync",
            "Conflict resolution",
            "LAN sync",
            "Bandwidth throttling",
            "System tray integration",
            "File versioning",
            "Offline mode"
        ]
    }


@router.post("/register-client")
async def register_desktop_client(
    client_name: str = Header(...),
    client_os: str = Header(...),
    client_version: str = Header(...),
    sync_folder: str = Header(...),
    current_user: dict = Depends(verify_api_key)
):
    """
    Register desktop sync client
    """
    
    db = await get_database()
    
    client_doc = {
        "user_id": str(current_user["_id"]),
        "client_name": client_name,
        "client_os": client_os,
        "client_version": client_version,
        "sync_folder": sync_folder,
        "registered_at": datetime.utcnow(),
        "last_sync": None,
        "status": "active"
    }
    
    result = await db.desktop_clients.insert_one(client_doc)
    client_id = str(result.inserted_id)
    
    return {
        "success": True,
        "client_id": client_id,
        "message": "Desktop client registered",
        "sync_folder": sync_folder
    }


@router.get("/sync-status")
async def get_sync_status(
    client_id: str = Header(...),
    current_user: dict = Depends(verify_api_key)
):
    """
    Get synchronization status
    """
    
    db = await get_database()
    
    try:
        client_object_id = ObjectId(client_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid client ID"
        )
    
    client = await db.desktop_clients.find_one({
        "_id": client_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Get sync queue
    queue = await db.sync_queue.count_documents({
        "client_id": client_id,
        "status": "pending"
    })
    
    return {
        "success": True,
        "status": {
            "client_id": client_id,
            "client_name": client["client_name"],
            "last_sync": client.get("last_sync").isoformat() if client.get("last_sync") else None,
            "pending_items": queue,
            "is_syncing": queue > 0,
            "status": client["status"]
        }
    }


@router.get("/changes")
async def get_server_changes(
    since: Optional[str] = Query(None, description="ISO timestamp"),
    limit: int = Query(100, le=1000),
    client_id: str = Header(...),
    current_user: dict = Depends(verify_api_key)
):
    """
    Get server-side changes for sync
    
    Returns files that changed on server since last sync
    """
    
    db = await get_database()
    
    # Parse timestamp
    if since:
        try:
            since_time = datetime.fromisoformat(since)
        except:
            since_time = datetime.utcnow() - timedelta(days=7)
    else:
        since_time = datetime.utcnow() - timedelta(days=7)
    
    # Get changes
    changes = await db.storage_data.find({
        "user_id": str(current_user["_id"]),
        "$or": [
            {"created_at": {"$gte": since_time}},
            {"updated_at": {"$gte": since_time}}
        ]
    }).limit(limit).to_list(None)
    
    # Get deletions
    deletions = await db.deleted_items.find({
        "user_id": str(current_user["_id"]),
        "deleted_at": {"$gte": since_time}
    }).to_list(None)
    
    return {
        "success": True,
        "timestamp": datetime.utcnow().isoformat(),
        "changes": [
            {
                "id": str(doc["_id"]),
                "path": f"/{doc.get('collection')}/{doc.get('data', {}).get('filename', 'file')}",
                "type": "file",
                "action": "created" if doc.get("created_at", datetime.min) >= since_time else "modified",
                "size": doc.get("data", {}).get("size", 0),
                "modified_at": doc.get("updated_at", doc.get("created_at")).isoformat(),
                "checksum": doc.get("data", {}).get("etag")
            }
            for doc in changes
        ],
        "deletions": [
            {
                "id": str(doc["data_id"]),
                "path": doc.get("path"),
                "deleted_at": doc["deleted_at"].isoformat()
            }
            for doc in deletions
        ]
    }


@router.post("/upload-batch")
async def upload_batch_files(
    files: List[dict],
    client_id: str = Header(...),
    current_user: dict = Depends(verify_api_key)
):
    """
    Upload batch of files from desktop client
    """
    
    db = await get_database()
    
    uploaded = []
    errors = []
    
    for file_info in files:
        try:
            # Create storage document
            doc = {
                "user_id": str(current_user["_id"]),
                "collection": "desktop_sync",
                "data": {
                    "filename": file_info.get("filename"),
                    "path": file_info.get("path"),
                    "size": file_info.get("size"),
                    "checksum": file_info.get("checksum")
                },
                "created_at": datetime.utcnow(),
                "synced_from": client_id
            }
            
            result = await db.storage_data.insert_one(doc)
            uploaded.append(str(result.inserted_id))
            
        except Exception as e:
            errors.append({
                "file": file_info.get("filename"),
                "error": str(e)
            })
    
    return {
        "success": True,
        "uploaded": len(uploaded),
        "errors": len(errors),
        "file_ids": uploaded,
        "error_details": errors if errors else None
    }


@router.post("/resolve-conflict")
async def resolve_sync_conflict(
    file_id: str,
    resolution: str = Query(..., description="server, client, or keep-both"),
    client_id: str = Header(...),
    current_user: dict = Depends(verify_api_key)
):
    """
    Resolve sync conflict
    
    Resolution options:
    - server: Keep server version
    - client: Use client version
    - keep-both: Rename and keep both
    """
    
    db = await get_database()
    
    try:
        file_object_id = ObjectId(file_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file ID"
        )
    
    file_doc = await db.storage_data.find_one({
        "_id": file_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not file_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found"
        )
    
    if resolution == "keep-both":
        # Create copy with conflict suffix
        filename = file_doc.get("data", {}).get("filename", "file")
        conflict_filename = f"{filename} (Conflicted Copy)"
        
        conflict_doc = file_doc.copy()
        conflict_doc.pop("_id")
        conflict_doc["data"]["filename"] = conflict_filename
        conflict_doc["created_at"] = datetime.utcnow()
        
        await db.storage_data.insert_one(conflict_doc)
    
    # Log resolution
    await db.sync_conflicts.update_one(
        {"file_id": file_id, "client_id": client_id},
        {
            "$set": {
                "resolved": True,
                "resolution": resolution,
                "resolved_at": datetime.utcnow()
            }
        }
    )
    
    return {
        "success": True,
        "file_id": file_id,
        "resolution": resolution,
        "message": "Conflict resolved"
    }


@router.get("/bandwidth-settings")
async def get_bandwidth_settings(
    client_id: str = Header(...),
    current_user: dict = Depends(verify_api_key)
):
    """
    Get bandwidth throttling settings
    """
    
    db = await get_database()
    
    try:
        client_object_id = ObjectId(client_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid client ID"
        )
    
    client = await db.desktop_clients.find_one({
        "_id": client_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    settings = client.get("bandwidth_settings", {
        "upload_limit_kbps": 0,  # 0 = unlimited
        "download_limit_kbps": 0,
        "auto_throttle": True
    })
    
    return {
        "success": True,
        "settings": settings
    }


@router.post("/pause-sync")
async def pause_sync(
    duration_minutes: int = Query(60, description="Pause duration in minutes"),
    client_id: str = Header(...),
    current_user: dict = Depends(verify_api_key)
):
    """
    Pause synchronization
    """
    
    db = await get_database()
    
    try:
        client_object_id = ObjectId(client_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid client ID"
        )
    
    resume_at = datetime.utcnow() + timedelta(minutes=duration_minutes)
    
    await db.desktop_clients.update_one(
        {"_id": client_object_id},
        {
            "$set": {
                "status": "paused",
                "paused_at": datetime.utcnow(),
                "resume_at": resume_at
            }
        }
    )
    
    return {
        "success": True,
        "message": f"Sync paused for {duration_minutes} minutes",
        "resume_at": resume_at.isoformat()
    }


@router.get("/selective-sync")
async def get_selective_sync_config(
    client_id: str = Header(...),
    current_user: dict = Depends(verify_api_key)
):
    """
    Get selective sync configuration
    
    Returns which folders are synced
    """
    
    db = await get_database()
    
    try:
        client_object_id = ObjectId(client_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid client ID"
        )
    
    client = await db.desktop_clients.find_one({
        "_id": client_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    selective_sync = client.get("selective_sync", {
        "enabled": True,
        "synced_folders": ["Documents", "Photos"],
        "excluded_folders": ["Temp", "Cache"]
    })
    
    return {
        "success": True,
        "selective_sync": selective_sync
    }