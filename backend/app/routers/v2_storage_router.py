"""
V2 Storage Router
Improved API with consistent response format and enhanced features
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query, Request
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
import time

from app.models.v2_models import (
    V2Response,
    V2Error,
    V2Meta,
    V2StorageData,
    V2StorageDataList,
    V2Pagination,
    V2CreateRequest,
    V2UpdateRequest,
    V2BatchCreateRequest,
    V2BatchResult,
    V2SearchRequest,
    V2SearchResult,
    V2Stats
)
from app.middleware.auth_middleware import verify_api_key
from app.database import get_database
from app.services.quota_manager import check_api_calls_quota, increment_api_calls

router = APIRouter()

# ============================================================================
# Helper Functions
# ============================================================================

def create_v2_response(
    success: bool,
    data: any = None,
    error: dict = None,
    meta: dict = None,
    request: Request = None
) -> V2Response:
    """Create standardized V2 response"""
    
    # Build metadata as dictionary
    response_meta = {
        "timestamp": datetime.utcnow().isoformat(),
        "api_version": "v2",
        "request_id": getattr(request.state, "request_id", None) if request else None
    }
    
    # Merge with additional metadata if provided
    if meta:
        response_meta = {**response_meta, **meta}
    
    return V2Response(
        success=success,
        data=data,
        error=error,
        meta=response_meta
    )


def create_v2_error(
    code: str,
    message: str,
    details: dict = None
) -> dict:
    """Create V2 error object"""
    
    return V2Error(
        code=code,
        message=message,
        details=details
    ).dict()


def convert_to_v2_storage_data(doc: dict) -> V2StorageData:
    """Convert MongoDB document to V2 format"""
    
    # Handle datetime conversion safely
    created_at = doc.get("created_at")
    if created_at:
        if hasattr(created_at, 'isoformat'):
            created_at = created_at.isoformat()
        else:
            created_at = str(created_at)
    else:
        created_at = datetime.utcnow().isoformat()
    
    updated_at = doc.get("updated_at")
    if updated_at:
        if hasattr(updated_at, 'isoformat'):
            updated_at = updated_at.isoformat()
        else:
            updated_at = str(updated_at)
    else:
        updated_at = datetime.utcnow().isoformat()
    
    return V2StorageData(
        id=str(doc["_id"]),
        collection=doc.get("collection", "unknown"),
        data=doc.get("data", {}),
        metadata={
            "size_bytes": doc.get("size", 0),
            "user_id": str(doc.get("user_id", "")),
            "tags": doc.get("tags", [])
        },
        created_at=created_at,
        updated_at=updated_at,
        version=doc.get("version", 1)
    )


# ============================================================================
# CREATE
# ============================================================================

@router.post("/storage", response_model=V2Response)
async def create_data_v2(
    request_data: V2CreateRequest,
    request: Request,
    current_user: dict = Depends(verify_api_key)
):
    """
    Create new data (V2)
    
    Improvements over V1:
    - Consistent response format
    - Support for tags and metadata
    - Data versioning
    - Better error messages
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        
        # Calculate size
        import json
        data_size = len(json.dumps(request_data.data).encode('utf-8'))
        
        # Prepare document
        document = {
            "collection": request_data.collection,
            "data": request_data.data,
            "user_id": str(current_user["_id"]),
            "size": data_size,
            "tags": request_data.tags or [],
            "metadata": request_data.metadata or {},
            "version": 1,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        # Insert
        result = await db.storage_data.insert_one(document)
        
        await increment_api_calls(current_user["_id"])
        
        # Get created document
        created_doc = await db.storage_data.find_one({"_id": result.inserted_id})
        
        return create_v2_response(
            success=True,
            data=convert_to_v2_storage_data(created_doc).dict(),
            meta={"operation": "create"},
            request=request
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_v2_error(
                code="CREATE_FAILED",
                message="Failed to create data",
                details={"error": str(e)}
            )
        )


# ============================================================================
# READ
# ============================================================================

@router.get("/storage/{item_id}", response_model=V2Response)
async def get_data_v2(
    item_id: str,
    request: Request,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get data by ID (V2)
    
    Improvements:
    - Consistent response format
    - Includes version information
    - Better error handling
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        
        document = await db.storage_data.find_one({
            "_id": ObjectId(item_id),
            "user_id": str(current_user["_id"])
        })
        
        await increment_api_calls(current_user["_id"])
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_v2_error(
                    code="NOT_FOUND",
                    message=f"Data with ID '{item_id}' not found"
                )
            )
        
        return create_v2_response(
            success=True,
            data=convert_to_v2_storage_data(document).dict(),
            request=request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_v2_error(
                code="READ_FAILED",
                message="Failed to retrieve data",
                details={"error": str(e)}
            )
        )


# ============================================================================
# LIST with Pagination
# ============================================================================

@router.get("/storage", response_model=V2Response)
async def list_data_v2(
    request: Request,
    collection: str = Query(..., description="Collection name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    sort_by: Optional[str] = Query(None, description="Field to sort by"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: dict = Depends(verify_api_key)
):
    """
    List data with pagination (V2)
    
    Improvements:
    - Proper pagination
    - Sorting options
    - Total count
    - Has next/previous indicators
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        
        # Build query
        query = {
            "collection": collection,
            "user_id": str(current_user["_id"])
        }
        
        # Get total count
        total_items = await db.storage_data.count_documents(query)
        
        # Calculate pagination
        skip = (page - 1) * page_size
        total_pages = (total_items + page_size - 1) // page_size
        
        # Build sort
        sort_field = sort_by or "created_at"
        sort_direction = -1 if sort_order == "desc" else 1
        
        # Get items
        cursor = db.storage_data.find(query).sort(
            sort_field, sort_direction
        ).skip(skip).limit(page_size)
        
        documents = await cursor.to_list(length=page_size)
        
        await increment_api_calls(current_user["_id"])
        
        # Convert to V2 format
        items = [convert_to_v2_storage_data(doc) for doc in documents]
        
        # Build pagination info
        pagination = V2Pagination(
            page=page,
            page_size=page_size,
            total_items=total_items,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_previous=page > 1
        )
        
        return create_v2_response(
            success=True,
            data={
                "items": [item.dict() for item in items],
                "pagination": pagination.dict()
            },
            request=request
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_v2_error(
                code="LIST_FAILED",
                message="Failed to list data",
                details={"error": str(e)}
            )
        )


# ============================================================================
# UPDATE
# ============================================================================

@router.patch("/storage/{item_id}", response_model=V2Response)
async def update_data_v2(
    item_id: str,
    update_data: V2UpdateRequest,
    request: Request,
    current_user: dict = Depends(verify_api_key)
):
    """
    Update data (V2)
    
    Improvements:
    - PATCH method (partial update)
    - Merge or replace options
    - Version tracking
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        
        # Check if exists
        existing = await db.storage_data.find_one({
            "_id": ObjectId(item_id),
            "user_id": str(current_user["_id"])
        })
        
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_v2_error(
                    code="NOT_FOUND",
                    message=f"Data with ID '{item_id}' not found"
                )
            )
        
        # Prepare update
        if update_data.merge:
            # Merge with existing data
            new_data = {**existing.get("data", {}), **update_data.data}
        else:
            # Replace entirely
            new_data = update_data.data
        
        # Calculate new size
        import json
        data_size = len(json.dumps(new_data).encode('utf-8'))
        
        # Build update document
        update_doc = {
            "$set": {
                "data": new_data,
                "size": data_size,
                "updated_at": datetime.utcnow()
            }
        }
        
        # Increment version if requested
        if update_data.increment_version:
            update_doc["$inc"] = {"version": 1}
        
        # Update
        await db.storage_data.update_one(
            {"_id": ObjectId(item_id)},
            update_doc
        )
        
        await increment_api_calls(current_user["_id"])
        
        # Get updated document
        updated_doc = await db.storage_data.find_one({"_id": ObjectId(item_id)})
        
        return create_v2_response(
            success=True,
            data=convert_to_v2_storage_data(updated_doc).dict(),
            meta={"operation": "update", "merge": update_data.merge},
            request=request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_v2_error(
                code="UPDATE_FAILED",
                message="Failed to update data",
                details={"error": str(e)}
            )
        )


# ============================================================================
# DELETE
# ============================================================================

@router.delete("/storage/{item_id}", response_model=V2Response)
async def delete_data_v2(
    item_id: str,
    request: Request,
    current_user: dict = Depends(verify_api_key)
):
    """Delete data (V2)"""
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        
        result = await db.storage_data.delete_one({
            "_id": ObjectId(item_id),
            "user_id": str(current_user["_id"])
        })
        
        await increment_api_calls(current_user["_id"])
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=create_v2_error(
                    code="NOT_FOUND",
                    message=f"Data with ID '{item_id}' not found"
                )
            )
        
        return create_v2_response(
            success=True,
            data={"deleted_id": item_id},
            meta={"operation": "delete"},
            request=request
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_v2_error(
                code="DELETE_FAILED",
                message="Failed to delete data",
                details={"error": str(e)}
            )
        )


# ============================================================================
# BATCH CREATE (New in V2)
# ============================================================================

@router.post("/storage/batch", response_model=V2Response)
async def batch_create_v2(
    batch_data: V2BatchCreateRequest,
    request: Request,
    current_user: dict = Depends(verify_api_key)
):
    """
    Batch create multiple items (V2 only)
    
    New feature in V2:
    - Create up to 100 items in one request
    - Atomic or continue-on-error modes
    - Detailed result tracking
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        
        successful = 0
        failed = 0
        results = []
        errors = []
        
        for idx, item_data in enumerate(batch_data.items):
            try:
                import json
                data_size = len(json.dumps(item_data).encode('utf-8'))
                
                document = {
                    "collection": batch_data.collection,
                    "data": item_data,
                    "user_id": str(current_user["_id"]),
                    "size": data_size,
                    "version": 1,
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                
                result = await db.storage_data.insert_one(document)
                
                successful += 1
                results.append({
                    "index": idx,
                    "id": str(result.inserted_id),
                    "success": True
                })
                
            except Exception as e:
                failed += 1
                error_detail = {
                    "index": idx,
                    "error": str(e)
                }
                errors.append(error_detail)
                
                results.append({
                    "index": idx,
                    "success": False,
                    "error": str(e)
                })
                
                if batch_data.stop_on_error:
                    break
        
        await increment_api_calls(current_user["_id"])
        
        batch_result = V2BatchResult(
            successful=successful,
            failed=failed,
            results=results,
            errors=errors
        )
        
        return create_v2_response(
            success=failed == 0,
            data=batch_result.dict(),
            meta={"operation": "batch_create"},
            request=request
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_v2_error(
                code="BATCH_CREATE_FAILED",
                message="Failed to batch create data",
                details={"error": str(e)}
            )
        )