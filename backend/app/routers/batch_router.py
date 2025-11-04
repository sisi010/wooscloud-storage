"""
Batch operations router
Handles bulk create, read, update, delete operations
"""

from fastapi import APIRouter, HTTPException, status, Depends
from typing import List
from datetime import datetime
from bson import ObjectId
import json

from app.models.batch_data import (
    BatchCreateRequest, BatchCreateResponse,
    BatchReadRequest, BatchReadResponse,
    BatchUpdateRequest, BatchUpdateResponse,
    BatchDeleteRequest, BatchDeleteResponse
)
from app.middleware.auth_middleware import verify_api_key
from app.services.quota_manager import (
    check_storage_quota,
    check_api_calls_quota,
    increment_api_calls,
    update_storage_usage
)
from app.services.smart_storage_router import SmartStorageRouter
from app.database import get_database

router = APIRouter()

# R2 storage will be set by main.py
r2_storage = None

@router.get("/test")
async def test_batch():
    """Test if batch router is working"""
    return {"status": "ok", "message": "Batch router is working!"}

@router.post("/create", response_model=BatchCreateResponse, status_code=status.HTTP_201_CREATED)
async def batch_create(
    request: BatchCreateRequest,
    current_user: dict = Depends(verify_api_key)
):
    """Create multiple data items in one request"""
    
    # Get user - handle both ObjectId and string
    user_id = api_key_doc["user_id"]
    if isinstance(user_id, str):
        try:
            user_id = ObjectId(user_id)
        except:
            pass
    user = await db.users.find_one({"_id": user_id})
    
    # Check API calls quota
    await check_api_calls_quota(user_id)
    
    if len(request.items) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No items provided"
        )
    
    if len(request.items) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 items allowed per batch"
        )
    
    db = await get_database()
    smart_router = SmartStorageRouter(
        mongodb_collection=db.storage_data,
        r2_storage=r2_storage
    )
    
    created_items = []
    failed_items = []
    total_size = 0
    
    for idx, item in enumerate(request.items):
        try:
            # Calculate size
            data_str = json.dumps(item.data, ensure_ascii=False)
            data_size = len(data_str.encode('utf-8'))
            
            # Check quota before each item
            await check_storage_quota(user_id, data_size)
            
            # Save using smart router
            result = await smart_router.save(
                user_id=user_id,
                collection=item.collection,
                data=item.data
            )
            
            # Get id
            item_id = result.get("id") or result.get("_id")
            
            if not item_id:
                raise Exception(f"No ID returned from save")
            
            created_items.append({
                "index": idx,
                "id": item_id,
                "collection": item.collection,
                "size": result.get("size", data_size),
                "storage_type": result.get("storage_type", "unknown")
            })
            
            total_size += data_size
            
        except Exception as e:
            failed_items.append({
                "index": idx,
                "collection": item.collection,
                "error": str(e)
            })
    
    # Update storage usage
    if total_size > 0:
        await update_storage_usage(user_id, total_size)
    
    # Increment API calls
    await increment_api_calls(user_id)
    
    return BatchCreateResponse(
        success=len(failed_items) == 0,
        created=len(created_items),
        items=created_items,
        failed=failed_items
    )

@router.post("/read", response_model=BatchReadResponse)
async def batch_read(
    request: BatchReadRequest,
    current_user: dict = Depends(verify_api_key)
):
    """Read multiple data items in one request"""
    
    
    user_id = current_user.get("_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    user_id = str(user_id)
    
    # Check API calls quota
    await check_api_calls_quota(user_id)
    
    if len(request.ids) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No IDs provided"
        )
    
    if len(request.ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 items allowed per batch"
        )
    
    db = await get_database()
    smart_router = SmartStorageRouter(
        mongodb_collection=db.storage_data,
        r2_storage=r2_storage
    )
    
    found_items = []
    not_found_ids = []
    
    for item_id in request.ids:
        try:
            result = await smart_router.retrieve(
                user_id=user_id,
                data_id=item_id
            )
            
            if result:
                found_items.append({
                    "id": result["id"],
                    "collection": result["collection"],
                    "data": result["data"],
                    "size": result["size"],
                    "storage_type": result["storage_type"],
                    "created_at": result["created_at"],
                    "updated_at": result["updated_at"]
                })
            else:
                not_found_ids.append(item_id)
                
        except Exception:
            not_found_ids.append(item_id)
    
    # Increment API calls
    await increment_api_calls(user_id)
    
    return BatchReadResponse(
        success=len(not_found_ids) == 0,
        found=len(found_items),
        items=found_items,
        not_found=not_found_ids
    )

@router.post("/update", response_model=BatchUpdateResponse)
async def batch_update(
    request: BatchUpdateRequest,
    current_user: dict = Depends(verify_api_key)
):
    """Update multiple data items in one request"""
    
   
    user_id = current_user.get("_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    user_id = str(user_id)
    
    # Check API calls quota
    await check_api_calls_quota(user_id)
    
    if len(request.items) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No items provided"
        )
    
    if len(request.items) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 items allowed per batch"
        )
    
    db = await get_database()
    smart_router = SmartStorageRouter(
        mongodb_collection=db.storage_data,
        r2_storage=r2_storage
    )
    
    updated_items = []
    failed_items = []
    
    for idx, item in enumerate(request.items):
        try:
            result = await smart_router.update_with_user(
                user_id=user_id,
                data_id=item.id,
                new_data=item.data
            )
            
            if result:
                updated_items.append({
                    "index": idx,
                    "id": item.id,
                    "size": result.get("size", 0),
                    "storage_type": result.get("storage_type", "unknown")
                })
            else:
                failed_items.append({
                    "index": idx,
                    "id": item.id,
                    "error": "Not found"
                })
                
        except Exception as e:
            failed_items.append({
                "index": idx,
                "id": item.id,
                "error": str(e)
            })
    
    # Increment API calls
    await increment_api_calls(user_id)
    
    return BatchUpdateResponse(
        success=len(failed_items) == 0,
        updated=len(updated_items),
        items=updated_items,
        failed=failed_items
    )

@router.post("/delete", response_model=BatchDeleteResponse)
async def batch_delete(
    request: BatchDeleteRequest,
    current_user: dict = Depends(verify_api_key)
):
    """Delete multiple data items in one request"""
    
    
    user_id = current_user.get("_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    user_id = str(user_id)
    
    # Check API calls quota
    await check_api_calls_quota(user_id)
    
    if len(request.ids) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No IDs provided"
        )
    
    if len(request.ids) > 100:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 100 items allowed per batch"
        )
    
    db = await get_database()
    smart_router = SmartStorageRouter(
        mongodb_collection=db.storage_data,
        r2_storage=r2_storage
    )
    
    deleted_ids = []
    not_found_ids = []
    total_freed = 0
    
    for item_id in request.ids:
        try:
            result = await smart_router.delete_with_user(
                user_id=user_id,
                data_id=item_id
            )
            
            if result["success"]:
                deleted_ids.append(item_id)
                total_freed += result.get("size", 0)
            else:
                not_found_ids.append(item_id)
                
        except Exception:
            not_found_ids.append(item_id)
    
    # Update storage usage
    if total_freed > 0:
        await update_storage_usage(user_id, -total_freed)
    
    # Increment API calls
    await increment_api_calls(user_id)
    
    return BatchDeleteResponse(
        success=len(not_found_ids) == 0,
        deleted=len(deleted_ids),
        ids=deleted_ids,
        not_found=not_found_ids
    )
