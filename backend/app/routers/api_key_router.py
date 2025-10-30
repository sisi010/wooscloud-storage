"""
API Key router
Handles API key generation and management
"""
from fastapi import APIRouter, HTTPException, status, Depends
from datetime import datetime
from bson import ObjectId
from typing import List

from app.services.auth_service import generate_api_key
from app.database import get_database
from app.middleware.auth_middleware import verify_token

router = APIRouter()

@router.post("/generate", response_model=dict, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    name: str,
    current_user: dict = Depends(verify_token)
):
    """
    Generate a new API key
    
    Requires valid JWT token
    """
    db = await get_database()
    
    # Generate unique API key
    api_key = generate_api_key()
    
    # Create API key document
    api_key_doc = {
        "user_id": current_user["_id"],
        "key": api_key,
        "name": name,
        "usage_count": 0,
        "last_used": None,
        "created_at": datetime.utcnow(),
        "is_active": True
    }
    
    result = await db.api_keys.insert_one(api_key_doc)
    
    return {
        "success": True,
        "message": "API key generated successfully",
        "api_key": api_key,
        "key_id": str(result.inserted_id),
        "name": name,
        "warning": "Please save this API key. You won't be able to see it again!"
    }

@router.get("/my-keys", response_model=dict)
async def list_api_keys(current_user: dict = Depends(verify_token)):
    """
    List all API keys for current user
    
    Requires valid JWT token
    """
    db = await get_database()
    
    # Find all API keys for user
    cursor = db.api_keys.find({"user_id": current_user["_id"]})
    api_keys = await cursor.to_list(length=100)
    
    # Format response (hide partial key for security)
    keys_list = []
    for key in api_keys:
        keys_list.append({
            "id": str(key["_id"]),
            "name": key["name"],
            "key": key["key"][:12] + "..." + key["key"][-4:],  # Show partial key
            "usage_count": key.get("usage_count", 0),
            "last_used": key.get("last_used").isoformat() if key.get("last_used") else None,
            "created_at": key["created_at"].isoformat(),
            "is_active": key.get("is_active", True)
        })
    
    return {
        "success": True,
        "keys": keys_list,
        "total": len(keys_list)
    }

@router.delete("/{key_id}", response_model=dict)
async def delete_api_key(
    key_id: str,
    current_user: dict = Depends(verify_token)
):
    """
    Delete an API key
    
    Requires valid JWT token
    """
    db = await get_database()
    
    try:
        key_object_id = ObjectId(key_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid key ID format"
        )
    
    # Find and verify ownership
    api_key = await db.api_keys.find_one({
        "_id": key_object_id,
        "user_id": current_user["_id"]
    })
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Delete API key
    await db.api_keys.delete_one({"_id": key_object_id})
    
    return {
        "success": True,
        "message": "API key deleted successfully"
    }

@router.put("/{key_id}/deactivate", response_model=dict)
async def deactivate_api_key(
    key_id: str,
    current_user: dict = Depends(verify_token)
):
    """
    Deactivate an API key (without deleting)
    
    Requires valid JWT token
    """
    db = await get_database()
    
    try:
        key_object_id = ObjectId(key_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid key ID format"
        )
    
    # Update API key
    result = await db.api_keys.update_one(
        {
            "_id": key_object_id,
            "user_id": current_user["_id"]
        },
        {"$set": {"is_active": False}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return {
        "success": True,
        "message": "API key deactivated successfully"
    }

@router.put("/{key_id}/activate", response_model=dict)
async def activate_api_key(
    key_id: str,
    current_user: dict = Depends(verify_token)
):
    """
    Activate a deactivated API key
    
    Requires valid JWT token
    """
    db = await get_database()
    
    try:
        key_object_id = ObjectId(key_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid key ID format"
        )
    
    # Update API key
    result = await db.api_keys.update_one(
        {
            "_id": key_object_id,
            "user_id": current_user["_id"]
        },
        {"$set": {"is_active": True}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    return {
        "success": True,
        "message": "API key activated successfully"
    }