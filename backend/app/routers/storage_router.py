"""
Storage router
Handles CRUD operations for cloud storage with R2 integration and Webhooks
OPTIMIZED VERSION with caching and indexing
"""
from fastapi import APIRouter, HTTPException, status, Depends, Query
from datetime import datetime
from bson import ObjectId
from typing import List, Optional, Dict, Any
import logging

from app.models.storage_data import StorageDataCreate, StorageDataUpdate, StorageStats
from app.middleware.auth_middleware import verify_api_key
from app.services.quota_manager import (
    check_storage_quota,
    check_api_calls_quota,
    increment_api_calls,
    update_storage_usage
)
from app.utils.performance_optimization import (
    get_storage_stats_optimized,
    get_storage_list_optimized,
    get_collection_counts_optimized,
    cache
)
from app.database import get_database
from app.config import settings
from app.services.webhook_service import WebhookService
from app.services.rate_limiter import get_rate_limiter

# R2 imports
from app.services.r2_storage import R2Storage
from app.services.smart_storage_router import SmartStorageRouter

logger = logging.getLogger(__name__)
router = APIRouter()

# R2 storage will be set by main.py
r2_storage = None

@router.post("/create", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_data(
    storage_data: StorageDataCreate,
    current_user: dict = Depends(verify_api_key)
):
    """
    Create new data entry
    Automatically routes to MongoDB or R2 based on size
    """
    db = await get_database()
    
    # Check API calls quota
    await check_api_calls_quota(current_user["_id"])
    
    # Initialize smart router
    smart_router = SmartStorageRouter(
        mongodb_collection=db.storage_data,
        r2_storage=r2_storage
    )
    
    # Calculate data size
    data_size = len(str(storage_data.data))
    
    # Check storage quota
    await check_storage_quota(current_user["_id"], data_size)
    
    try:
        # Save using smart router
        document = await smart_router.save(
            user_id=str(current_user["_id"]),
            collection=storage_data.collection,
            data=storage_data.data
        )
        
        data_id = str(document["_id"])
        storage_type = document["storage_type"]
        
        # Update storage usage
        await update_storage_usage(current_user["_id"], document["size"])
        
        # Increment API calls counter
        await increment_api_calls(current_user["_id"])
        
        # Clear cache for this user
        await cache.delete(f"stats:{current_user['_id']}")
        await cache.delete(f"collections:{current_user['_id']}")
        
        # Trigger webhook
        try:
            webhook_service = WebhookService(db)
            await webhook_service.trigger_event(
                user_id=str(current_user["_id"]),
                event="data.created",
                payload={
                    "id": data_id,
                    "collection": storage_data.collection,
                    "storage_type": storage_type,
                    "size": document["size"]
                }
            )
        except Exception as e:
            logger.warning(f"Failed to trigger webhook: {e}")
        
        return {
            "success": True,
            "id": data_id,
            "storage_type": storage_type,
            "size": document["size"],
            "created_at": document["created_at"].isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to create data: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get("/read/{data_id}", response_model=dict)
async def read_data(
    data_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Read data by ID
    Automatically retrieves from MongoDB or R2
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
    
    # Initialize smart router
    smart_router = SmartStorageRouter(
        mongodb_collection=db.storage_data,
        r2_storage=r2_storage
    )
    
    # Get metadata
    doc = await db.storage_data.find_one({
        "_id": data_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )
    
    # Get actual data
    data = await smart_router.get(data_id)
    
    if data is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve data"
        )
    
    # Increment API calls counter
    await increment_api_calls(current_user["_id"])
    
    return {
        "success": True,
        "id": str(doc["_id"]),
        "collection": doc["collection"],
        "data": data,
        "storage_type": doc.get("storage_type", "mongodb"),
        "size": doc["size"],
        "created_at": doc["created_at"].isoformat(),
        "updated_at": doc["updated_at"].isoformat()
    }

@router.get("/list", response_model=dict)
async def list_data(
    collection: Optional[str] = Query(None, description="Filter by collection name"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    current_user: dict = Depends(verify_api_key)
):
    """
    List all data entries (OPTIMIZED)
    Uses indexes and projection for better performance
    """
    
    db = await get_database()
    
    # Check API calls quota
    await check_api_calls_quota(current_user["_id"])
    
    # Use optimized version
    documents = await get_storage_list_optimized(
        db,
        str(current_user["_id"]),
        skip,
        limit,
        collection
    )
    
    # Get total count
    query = {"user_id": str(current_user["_id"])}
    if collection:
        query["collection"] = collection
    total_count = await db.storage_data.count_documents(query)
    
    # Format response
    formatted_data = []
    for doc in documents:
        formatted_item = {
            "id": str(doc["_id"]),
            "collection": doc.get("collection", "unknown"),
            "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
            "updated_at": doc.get("updated_at").isoformat() if doc.get("updated_at") else None,
            "tags": doc.get("tags", []),
            "metadata": doc.get("metadata", {})
        }
        formatted_data.append(formatted_item)
    
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
    Automatically updates in MongoDB or R2
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
    
    # Check ownership
    doc = await db.storage_data.find_one({
        "_id": data_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )
    
    old_size = doc["size"]
    
    # Initialize smart router
    smart_router = SmartStorageRouter(
        mongodb_collection=db.storage_data,
        r2_storage=r2_storage
    )
    
    # Update
    updated_doc = await smart_router.update(data_id, update_data.data)
    
    if not updated_doc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update data"
        )
    
    # Calculate size difference
    new_size = updated_doc["size"]
    size_diff = new_size - old_size
    
    # Update storage usage
    if size_diff != 0:
        await update_storage_usage(current_user["_id"], size_diff)
    
    # Increment API calls counter
    await increment_api_calls(current_user["_id"])
    
    # Clear cache
    await cache.delete(f"stats:{current_user['_id']}")
    
    # Trigger webhook
    try:
        webhook_service = WebhookService(db)
        await webhook_service.trigger_event(
            user_id=str(current_user["_id"]),
            event="data.updated",
            payload={
                "id": data_id,
                "collection": doc["collection"],
                "size_change": size_diff
            }
        )
    except Exception as e:
        logger.warning(f"Failed to trigger webhook: {e}")
    
    return {
        "success": True,
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
    Automatically deletes from MongoDB or R2
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
    
    # Check ownership
    doc = await db.storage_data.find_one({
        "_id": data_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )
    
    collection_name = doc["collection"]
    freed_space = doc["size"]
    
    # Initialize smart router
    smart_router = SmartStorageRouter(
        mongodb_collection=db.storage_data,
        r2_storage=r2_storage
    )
    
    # Delete
    success = await smart_router.delete(data_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete data"
        )
    
    # Update storage usage (decrease)
    await update_storage_usage(current_user["_id"], -freed_space)
    
    # Increment API calls counter
    await increment_api_calls(current_user["_id"])
    
    # Clear cache
    await cache.delete(f"stats:{current_user['_id']}")
    await cache.delete(f"collections:{current_user['_id']}")
    
    # Trigger webhook
    try:
        webhook_service = WebhookService(db)
        await webhook_service.trigger_event(
            user_id=str(current_user["_id"]),
            event="data.deleted",
            payload={
                "id": data_id,
                "collection": collection_name,
                "freed_space": freed_space
            }
        )
    except Exception as e:
        logger.warning(f"Failed to trigger webhook: {e}")
    
    return {
        "success": True,
        "id": data_id,
        "freed_space": freed_space
    }

@router.get("/stats", response_model=dict)
async def get_stats(current_user: dict = Depends(verify_api_key)):
    """
    Get storage usage statistics (OPTIMIZED)
    Uses caching and aggregation for better performance
    """
    db = await get_database()
    
    # Use optimized version with caching
    optimized_stats = await get_storage_stats_optimized(
        db, 
        str(current_user["_id"])
    )
    
    # Get user-specific data
    user = await db.users.find_one({"_id": current_user["_id"]})
    
    storage_used = user.get("storage_used", 0)
    storage_limit = user.get("storage_limit", 500 * 1024 * 1024)  # 500MB default
    api_calls_count = user.get("api_calls_count", 0)
    api_calls_limit = user.get("api_calls_limit", 10000)  # 10K default
    
    # Calculate percentage
    storage_percent = (storage_used / storage_limit * 100) if storage_limit > 0 else 0
    
    # Count by storage type
    mongodb_count = await db.storage_data.count_documents({
        "user_id": str(current_user["_id"]),
        "storage_type": "mongodb"
    })
    
    r2_count = await db.storage_data.count_documents({
        "user_id": str(current_user["_id"]),
        "storage_type": "r2"
    })
    
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
                "remaining": max(0, api_calls_limit - api_calls_count)
            },
            "documents": {
                "total": optimized_stats.get("total_documents", 0),
                "collections": optimized_stats.get("total_collections", 0),
                "mongodb": mongodb_count,
                "r2": r2_count
            },
            "plan": user.get("plan", "free"),
            "r2_enabled": settings.R2_ENABLED,
            "from_cache": optimized_stats.get("from_cache", False)
        }
    }

@router.get("/collections", response_model=dict)
async def list_collections(current_user: dict = Depends(verify_api_key)):
    """
    List all collections with statistics (OPTIMIZED)
    Uses caching and aggregation
    """
    db = await get_database()
    
    # Use optimized version with caching
    collection_counts = await get_collection_counts_optimized(
        db,
        str(current_user["_id"])
    )
    
    # Aggregate detailed stats
    pipeline = [
        {"$match": {"user_id": str(current_user["_id"])}},
        {"$group": {
            "_id": "$collection",
            "count": {"$sum": 1},
            "total_size": {"$sum": "$size"},
            "mongodb_count": {
                "$sum": {"$cond": [{"$eq": ["$storage_type", "mongodb"]}, 1, 0]}
            },
            "r2_count": {
                "$sum": {"$cond": [{"$eq": ["$storage_type", "r2"]}, 1, 0]}
            }
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
            "size_kb": round(col["total_size"] / 1024, 2),
            "mongodb_count": col.get("mongodb_count", 0),
            "r2_count": col.get("r2_count", 0)
        })
    
    return {
        "success": True,
        "collections": collections_list,
        "total_collections": len(collections_list)
    }
    
@router.get("/rate-limit")
async def get_rate_limit_info(current_user: dict = Depends(verify_api_key)):
    """
    Get current rate limit status
    
    Returns information about API rate limits and current usage
    """
    
    rate_limiter = get_rate_limiter()
    stats = await rate_limiter.get_stats(str(current_user["_id"]))
    
    plan = current_user.get("plan", "free")
    
    # Get limits
    hourly_limit = rate_limiter._get_limits(plan, "hour")
    monthly_limit = rate_limiter._get_limits(plan, "month")
    
    return {
        "success": True,
        "plan": plan,
        "limits": {
            "hourly": {
                "limit": hourly_limit if hourly_limit < 999999999 else -1,
                "used": stats.get("hour", {}).get("count", 0),
                "remaining": max(0, hourly_limit - stats.get("hour", {}).get("count", 0)) if hourly_limit < 999999999 else -1,
                "reset": stats.get("hour", {}).get("reset_time")
            },
            "monthly": {
                "limit": monthly_limit if monthly_limit < 999999999 else -1,
                "used": stats.get("month", {}).get("count", 0),
                "remaining": max(0, monthly_limit - stats.get("month", {}).get("count", 0)) if monthly_limit < 999999999 else -1,
                "reset": stats.get("month", {}).get("reset_time")
            }
        }
    }