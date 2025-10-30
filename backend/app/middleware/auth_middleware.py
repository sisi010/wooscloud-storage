"""
Authentication middleware
Verifies API keys and JWT tokens
"""
from fastapi import Header, HTTPException, status
from app.database import get_database
from app.services.auth_service import decode_access_token
from bson import ObjectId

async def verify_api_key(x_api_key: str = Header(..., alias="X-API-Key")) -> dict:
    """
    Verify API key and return user
    
    Args:
        x_api_key: API key from header
    
    Returns:
        User document
    
    Raises:
        HTTPException: If API key is invalid
    """
    db = await get_database()
    
    # Find API key
    api_key_doc = await db.api_keys.find_one({"key": x_api_key, "is_active": True})
    
    if not api_key_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key"
        )
    
    # Get user
    user = await db.users.find_one({"_id": api_key_doc["user_id"]})
    
    if not user or not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    # Update last used timestamp
    from datetime import datetime
    await db.api_keys.update_one(
        {"_id": api_key_doc["_id"]},
        {
            "$set": {"last_used": datetime.utcnow()},
            "$inc": {"usage_count": 1}
        }
    )
    
    return user

async def verify_token(authorization: str = Header(...)) -> dict:
    """
    Verify JWT token and return user
    
    Args:
        authorization: Bearer token from header
    
    Returns:
        User document
    
    Raises:
        HTTPException: If token is invalid
    """
    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    token = authorization.replace("Bearer ", "")
    payload = decode_access_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload"
        )
    
    db = await get_database()
    user = await db.users.find_one({"email": email})
    
    if not user or not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user