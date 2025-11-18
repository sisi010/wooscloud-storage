from fastapi import Header, HTTPException, status, Request
from app.database import get_database
from app.services.auth_service import decode_access_token
from bson import ObjectId
from datetime import datetime

async def verify_api_key(
    x_api_key: str = Header(..., alias="X-API-Key"),
    request: Request = None
) -> dict:
    db = await get_database()
    api_key_doc = await db.api_keys.find_one({"key": x_api_key, "is_active": True})
    
    if not api_key_doc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")
    
    user_id = api_key_doc["user_id"]
    if isinstance(user_id, str):
        try:
            user_id = ObjectId(user_id)
        except:
            pass
    
    user = await db.users.find_one({"_id": user_id})
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    await db.api_keys.update_one({"_id": api_key_doc["_id"]}, {"$set": {"last_used": datetime.utcnow()}, "$inc": {"usage_count": 1}})
    
    # Set user in request state for rate limiting
    if request:
        request.state.user = user
    
    return user

async def verify_token(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth")
    
    token = authorization.replace("Bearer ", "")
    
    try:
        payload = decode_access_token(token)
    except:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid payload")
    
    db = await get_database()
    user = await db.users.find_one({"email": email})
    
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    
    return user

# Helper function for audit middleware
async def get_user_from_api_key(api_key: str, db):
    """Get user from API key (for audit logging)"""
    
    # Find API key
    api_key_doc = await db.api_keys.find_one({"key": api_key})
    
    if not api_key_doc:
        return None
    
    # Get user
    user = await db.users.find_one({"_id": api_key_doc["user_id"]})
    
    return user