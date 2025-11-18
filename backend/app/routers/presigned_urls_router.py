"""
Pre-signed URLs Router
Generate temporary secure links for file sharing without authentication
Similar to AWS S3 Pre-signed URLs
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from fastapi.responses import RedirectResponse
from datetime import datetime, timedelta
from typing import Optional
import jwt
import secrets
from bson import ObjectId

from app.middleware.auth_middleware import verify_api_key
from app.database import get_database
from app.config import settings

router = APIRouter(prefix="/presigned", tags=["Pre-signed URLs"])

# JWT secret for signing URLs (use your app's secret)
PRESIGNED_SECRET = settings.jwt_secret + "_presigned"


@router.post("/generate")
async def generate_presigned_url(
    data_id: str = Query(..., description="Data ID to share"),
    expires_in: int = Query(3600, ge=60, le=604800, description="Expiration time in seconds (1min - 7days)"),
    max_downloads: Optional[int] = Query(None, ge=1, le=1000, description="Maximum download count"),
    password: Optional[str] = Query(None, description="Optional password protection"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Generate a pre-signed URL for temporary access
    
    Features:
    - Time-based expiration (1min to 7 days)
    - Download limit
    - Optional password protection
    - No authentication required to access
    
    Returns shareable URL
    """
    
    db = await get_database()
    
    # Verify data exists and user owns it
    try:
        data_object_id = ObjectId(data_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data ID format"
        )
    
    # Check in V1 (storage_data)
    doc = await db.storage_data.find_one({
        "_id": data_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found or access denied"
        )
    
    # Generate unique share ID
    share_id = secrets.token_urlsafe(16)
    
    # Create expiration time
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    
    # Create JWT token with claims
    token_data = {
        "share_id": share_id,
        "data_id": data_id,
        "user_id": str(current_user["_id"]),
        "expires_at": expires_at.isoformat(),
        "max_downloads": max_downloads,
        "has_password": password is not None
    }
    
    # Sign the token
    signed_token = jwt.encode(
        token_data,
        PRESIGNED_SECRET,
        algorithm="HS256"
    )
    
    # Store share info in database
    share_doc = {
        "share_id": share_id,
        "data_id": data_id,
        "user_id": str(current_user["_id"]),
        "token": signed_token,
        "password": password,  # Store hashed in production!
        "expires_at": expires_at,
        "max_downloads": max_downloads,
        "download_count": 0,
        "created_at": datetime.utcnow(),
        "is_active": True,
        "metadata": {
            "collection": doc.get("collection"),
            "storage_type": doc.get("storage_type", "mongodb")
        }
    }
    
    await db.presigned_urls.insert_one(share_doc)
    
    # Generate shareable URL
    base_url = settings.base_url or "http://127.0.0.1:8000"
    share_url = f"{base_url}/api/presigned/access/{share_id}?token={signed_token}"
    
    return {
        "success": True,
        "share_id": share_id,
        "share_url": share_url,
        "expires_at": expires_at.isoformat(),
        "expires_in_seconds": expires_in,
        "max_downloads": max_downloads,
        "has_password": password is not None,
        "metadata": {
            "data_id": data_id,
            "collection": doc.get("collection"),
            "created_at": datetime.utcnow().isoformat()
        }
    }


@router.get("/access/{share_id}")
async def access_presigned_url(
    share_id: str,
    token: str = Query(..., description="Signed token"),
    password: Optional[str] = Query(None, description="Password if required")
):
    """
    Access data via pre-signed URL
    
    No authentication required!
    Validates token, expiration, download limit, and password
    """
    
    db = await get_database()
    
    # Verify token signature
    try:
        token_data = jwt.decode(
            token,
            PRESIGNED_SECRET,
            algorithms=["HS256"]
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Share link has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid share link"
        )
    
    # Verify share_id matches
    if token_data.get("share_id") != share_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid share link"
        )
    
    # Get share info from database
    share_doc = await db.presigned_urls.find_one({
        "share_id": share_id,
        "is_active": True
    })
    
    if not share_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found or has been revoked"
        )
    
    # Check expiration
    if datetime.utcnow() > share_doc["expires_at"]:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Share link has expired"
        )
    
    # Check download limit
    if share_doc.get("max_downloads"):
        if share_doc["download_count"] >= share_doc["max_downloads"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Download limit reached"
            )
    
    # Check password
    if share_doc.get("password"):
        if not password or password != share_doc["password"]:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect password"
            )
    
    # Get actual data
    data_id = share_doc["data_id"]
    try:
        data_object_id = ObjectId(data_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data ID"
        )
    
    doc = await db.storage_data.find_one({"_id": data_object_id})
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )
    
    # Increment download count
    await db.presigned_urls.update_one(
        {"share_id": share_id},
        {"$inc": {"download_count": 1}}
    )
    
    # Return data
    return {
        "success": True,
        "data": doc.get("data"),
        "metadata": {
            "id": str(doc["_id"]),
            "collection": doc.get("collection"),
            "storage_type": doc.get("storage_type", "mongodb"),
            "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
            "download_count": share_doc["download_count"] + 1,
            "remaining_downloads": (
                share_doc["max_downloads"] - share_doc["download_count"] - 1
                if share_doc.get("max_downloads")
                else None
            )
        }
    }


@router.delete("/revoke/{share_id}")
async def revoke_presigned_url(
    share_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Revoke a pre-signed URL
    
    Only the creator can revoke
    """
    
    db = await get_database()
    
    # Find and verify ownership
    share_doc = await db.presigned_urls.find_one({
        "share_id": share_id,
        "user_id": str(current_user["_id"])
    })
    
    if not share_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Share link not found"
        )
    
    # Deactivate
    await db.presigned_urls.update_one(
        {"share_id": share_id},
        {"$set": {"is_active": False, "revoked_at": datetime.utcnow()}}
    )
    
    return {
        "success": True,
        "message": "Share link revoked",
        "share_id": share_id
    }


@router.get("/list")
async def list_presigned_urls(
    limit: int = Query(20, ge=1, le=100),
    skip: int = Query(0, ge=0),
    active_only: bool = Query(True, description="Show only active links"),
    current_user: dict = Depends(verify_api_key)
):
    """
    List all pre-signed URLs created by user
    """
    
    db = await get_database()
    
    # Build query
    query = {"user_id": str(current_user["_id"])}
    if active_only:
        query["is_active"] = True
        query["expires_at"] = {"$gt": datetime.utcnow()}
    
    # Get shares
    cursor = db.presigned_urls.find(query).sort("created_at", -1).skip(skip).limit(limit)
    shares = await cursor.to_list(length=limit)
    
    # Count total
    total = await db.presigned_urls.count_documents(query)
    
    # Format response
    formatted_shares = []
    base_url = settings.base_url or "http://127.0.0.1:8000"
    
    for share in shares:
        formatted_shares.append({
            "share_id": share["share_id"],
            "share_url": f"{base_url}/api/presigned/access/{share['share_id']}?token={share['token']}",
            "data_id": share["data_id"],
            "expires_at": share["expires_at"].isoformat(),
            "is_expired": datetime.utcnow() > share["expires_at"],
            "is_active": share["is_active"],
            "max_downloads": share.get("max_downloads"),
            "download_count": share["download_count"],
            "has_password": share.get("password") is not None,
            "created_at": share["created_at"].isoformat(),
            "metadata": share.get("metadata", {})
        })
    
    return {
        "success": True,
        "total": total,
        "shares": formatted_shares,
        "pagination": {
            "limit": limit,
            "skip": skip
        }
    }


@router.get("/stats")
async def presigned_stats(
    current_user: dict = Depends(verify_api_key)
):
    """
    Get statistics for pre-signed URLs
    """
    
    db = await get_database()
    
    user_id = str(current_user["_id"])
    
    # Total shares created
    total_shares = await db.presigned_urls.count_documents({"user_id": user_id})
    
    # Active shares
    active_shares = await db.presigned_urls.count_documents({
        "user_id": user_id,
        "is_active": True,
        "expires_at": {"$gt": datetime.utcnow()}
    })
    
    # Expired shares
    expired_shares = await db.presigned_urls.count_documents({
        "user_id": user_id,
        "expires_at": {"$lte": datetime.utcnow()}
    })
    
    # Total downloads
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": None, "total_downloads": {"$sum": "$download_count"}}}
    ]
    
    result = await db.presigned_urls.aggregate(pipeline).to_list(None)
    total_downloads = result[0]["total_downloads"] if result else 0
    
    return {
        "success": True,
        "total_shares": total_shares,
        "active_shares": active_shares,
        "expired_shares": expired_shares,
        "revoked_shares": total_shares - active_shares - expired_shares,
        "total_downloads": total_downloads
    }