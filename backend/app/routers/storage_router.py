"""
Storage router
Handles CRUD operations for cloud storage
This is the core functionality of WoosCloud Storage
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from datetime import datetime
from bson import ObjectId
from typing import List, Optional, Dict, Any

from app.models.storage_data import StorageDataCreate, StorageDataUpdate, StorageStats
from app.middleware.auth_middleware import verify_api_key
from app.services.quota_manager import (
    check_storage_quota,
    check_api_calls_quota,
    increment_api_calls,
    update_storage_usage
)
from app.database import get_database
from app.config import settings

router = APIRouter()

@router.post("/create", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_data(
    storage_data: StorageDataCreate,
    current_user: dict = Depends(verify_api_key)
):
    """
    Create new data entry
    
    Requires valid API key
    
    Example:
        POST /api/storage/create
        Headers: X-API-Key: wai_abc123...
        Body: {
            "collection": "users",
            "data": {"name": "홍길동", "age": 30}
        }
    """
    db = await get_database()
    
    # Check API calls quota
    await check_api_calls_quota(current_user["_id"])
    
    # Calculate data size
    data_size = len(str(storage_data.data))
    
    # Check storage quota
    await check_storage_quota(current_user["_id"], data_size)
    
    # Create storage document
    storage_doc = {
        "user_id": current_user["_id"],
        "collection": storage_data.collection,
        "data": storage_data.data,
        "size": data_size,
        "provider": "mongodb",  # Phase 1: MongoDB only
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }
    
    result = await db.storage_data.insert_one(storage_doc)
    
    # Update storage usage
    await update_storage_usage(current_user["_id"], data_size)
    
    # Increment API calls counter
    await increment_api_calls(current_user["_id"])
    
    return {
        "success": True,
        "id": str(result.inserted_id),
        "message": "Data created successfully",
        "collection": storage_data.collection,
        "size": data_size
    }

@router.get("/read/{data_id}", response_model=dict)
async def read_data(
    data_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Read data by ID
    
    Requires valid API key
    """
    db = await get_database()
    
    # Check API calls quota
    await check_api_calls_quota(current_user["_id"])
    
    try:
        data_object_id = ObjectId(data_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data ID format"
        )
    
    # Find data (only user's own data)
    storage_data = await db.storage_data.find_one({
        "_id": data_object_id,
        "user_id": current_user["_id"]
    })
    
    if not storage_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )
    
    # Increment API calls counter
    await increment_api_calls(current_user["_id"])
    
    return {
        "success": True,
        "id": str(storage_data["_id"]),
        "collection": storage_data["collection"],
        "data": storage_data["data"],
        "created_at": storage_data["created_at"].isoformat(),
        "updated_at": storage_data["updated_at"].isoformat()
    }

@router.get("/list", response_model=dict)
async def list_data(
    collection: Optional[str] = Query(None, description="Filter by collection name"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: dict = Depends(verify_api_key)
):
    """
    List all data (with pagination and filtering)
    
    Requires valid API key
    
    Example:
        GET /api/storage/list?collection=users&limit=10&skip=0
        Headers: X-API-Key: wai_abc123...
    """
    db = await get_database()
    
    # Check API calls quota
    await check_api_calls_quota(current_user["_id"])
    
    # Build query
    query = {"user_id": current_user["_id"]}
    if collection:
        query["collection"] = collection
    
    # Get data
    cursor = db.storage_data.find(query).skip(skip).limit(limit).sort("created_at", -1)
    data_list = await cursor.to_list(length=limit)
    
    # Get total count
    total_count = await db.storage_data.count_documents(query)
    
    # Format response
    formatted_data = []
    for item in data_list:
        formatted_data.append({
            "id": str(item["_id"]),
            "collection": item["collection"],
            "data": item["data"],
            "size": item["size"],
            "created_at": item["created_at"].isoformat(),
            "updated_at": item["updated_at"].isoformat()
        })
    
    # Increment API calls counter
    await increment_api_calls(current_user["_id"])
    
    return {
        "success": True,
        "data": formatted_data,
        "total": total_count,
        "count": len(formatted_data),
        "limit": limit,
        "skip": skip
    }

@router.put("/update/{data_id}", response_model=dict)
async def update_data(
    data_id: str,
    update_data: StorageDataUpdate,
    current_user: dict = Depends(verify_api_key)
):
    """
    Update data by ID
    
    Requires valid API key
    """
    db = await get_database()
    
    # Check API calls quota
    await check_api_calls_quota(current_user["_id"])
    
    try:
        data_object_id = ObjectId(data_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data ID format"
        )
    
    # Find existing data
    existing_data = await db.storage_data.find_one({
        "_id": data_object_id,
        "user_id": current_user["_id"]
    })
    
    if not existing_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )
    
    # Calculate size difference
    old_size = existing_data["size"]
    new_size = len(str(update_data.data))
    size_diff = new_size - old_size
    
    # Check storage quota (only if size increased)
    if size_diff > 0:
        await check_storage_quota(current_user["_id"], size_diff)
    
    # Update data
    await db.storage_data.update_one(
        {"_id": data_object_id},
        {
            "$set": {
                "data": update_data.data,
                "size": new_size,
                "updated_at": datetime.utcnow()
            }
        }
    )
    
    # Update storage usage
    await update_storage_usage(current_user["_id"], size_diff)
    
    # Increment API calls counter
    await increment_api_calls(current_user["_id"])
    
    return {
        "success": True,
        "message": "Data updated successfully",
        "id": data_id,
        "size_change": size_diff
    }

@router.delete("/delete/{data_id}", response_model=dict)
async def delete_data(
    data_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Delete data by ID
    
    Requires valid API key
    """
    db = await get_database()
    
    # Check API calls quota
    await check_api_calls_quota(current_user["_id"])
    
    try:
        data_object_id = ObjectId(data_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data ID format"
        )
    
    # Find and verify ownership
    storage_data = await db.storage_data.find_one({
        "_id": data_object_id,
        "user_id": current_user["_id"]
    })
    
    if not storage_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )
    
    # Delete data
    await db.storage_data.delete_one({"_id": data_object_id})
    
    # Update storage usage (decrease)
    await update_storage_usage(current_user["_id"], -storage_data["size"])
    
    # Increment API calls counter
    await increment_api_calls(current_user["_id"])
    
    return {
        "success": True,
        "message": "Data deleted successfully",
        "id": data_id,
        "freed_space": storage_data["size"]
    }

@router.get("/stats", response_model=dict)
async def get_stats(current_user: dict = Depends(verify_api_key)):
    """
    Get storage usage statistics
    
    Requires valid API key
    """
    db = await get_database()
    
    # Get fresh user data
    user = await db.users.find_one({"_id": current_user["_id"]})
    
    storage_used = user.get("storage_used", 0)
    storage_limit = user.get("storage_limit", settings.FREE_STORAGE_LIMIT)
    api_calls_count = user.get("api_calls_count", 0)
    api_calls_limit = user.get("api_calls_limit", settings.FREE_API_CALLS_LIMIT)
    
    # Calculate percentage
    storage_percent = (storage_used / storage_limit * 100) if storage_limit > 0 else 0
    
    return {
        "success": True,
        "stats": {
            "storage": {
                "used": storage_used,
                "limit": storage_limit,
                "percent": round(storage_percent, 2),
                "used_mb": round(storage_used / 1024 / 1024, 2),
                "limit_mb": round(storage_limit / 1024 / 1024, 2)
            },
            "api_calls": {
                "count": api_calls_count,
                "limit": api_calls_limit,
                "remaining": max(0, api_calls_limit - api_calls_count) if user.get("plan") == "free" else "unlimited"
            },
            "plan": user.get("plan", "free")
        }
    }

@router.get("/collections", response_model=dict)
async def list_collections(current_user: dict = Depends(verify_api_key)):
    """
    List all collections with statistics
    
    Requires valid API key
    """
    db = await get_database()
    
    # Aggregate collections
    pipeline = [
        {"$match": {"user_id": current_user["_id"]}},
        {"$group": {
            "_id": "$collection",
            "count": {"$sum": 1},
            "total_size": {"$sum": "$size"}
        }},
        {"$sort": {"count": -1}}
    ]
    
    cursor = db.storage_data.aggregate(pipeline)
    collections = await cursor.to_list(length=100)
    
    # Format response
    collections_list = []
    for col in collections:
        collections_list.append({
            "name": col["_id"],
            "count": col["count"],
            "size": col["total_size"],
            "size_kb": round(col["total_size"] / 1024, 2)
        })
    
    return {
        "success": True,
        "collections": collections_list,
        "total_collections": len(collections_list)
    }