"""
Quota management service
Handles storage limits and API rate limits
"""
from fastapi import HTTPException
from bson import ObjectId
from app.database import get_database
from app.config import settings

async def check_storage_quota(user_id, additional_size: int):
    """
    Check if user has enough storage quota
    
    Args:
        user_id: User ID (ObjectId or string)
        additional_size: Size of new data in bytes
    
    Raises:
        HTTPException: If quota exceeded
    """
    # Convert to string if ObjectId
    user_id_str = str(user_id)
    
    db = await get_database()
    user = await db.users.find_one({"_id": ObjectId(user_id_str)})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_usage = user.get("storage_used", 0)
    storage_limit = user.get("storage_limit", settings.FREE_STORAGE_LIMIT)
    
    if current_usage + additional_size > storage_limit:
        # Calculate how much over the limit
        over_limit_mb = (current_usage + additional_size - storage_limit) / 1024 / 1024
        
        raise HTTPException(
            status_code=403,
            detail={
                "error": "Storage limit exceeded",
                "message": f"You need {over_limit_mb:.2f} MB more storage. Please upgrade your plan.",
                "current_usage": current_usage,
                "limit": storage_limit,
                "upgrade_url": "https://woos-ai.com/pricing.html"
            }
        )

async def check_api_calls_quota(user_id):
    """
    Check if user has API calls remaining
    
    Args:
        user_id: User ID (ObjectId or string)
    
    Raises:
        HTTPException: If quota exceeded
    """
    # Convert to string if ObjectId
    user_id_str = str(user_id)
    
    db = await get_database()
    user = await db.users.find_one({"_id": ObjectId(user_id_str)})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # STARTER and PREMIUM plans have unlimited API calls
    user_plan = user.get("plan", "free").lower()
    if user_plan in ["starter", "premium", "pro"]:
        return
    
    api_calls_count = user.get("api_calls_count", 0)
    api_calls_limit = user.get("api_calls_limit", settings.FREE_API_CALLS_LIMIT)
    
    if api_calls_count >= api_calls_limit:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "API calls limit exceeded",
                "message": "You've reached your monthly API calls limit. Please upgrade for unlimited calls.",
                "current_usage": api_calls_count,
                "limit": api_calls_limit,
                "upgrade_url": "https://woos-ai.com/pricing.html"
            }
        )

async def increment_api_calls(user_id):
    """
    Increment user's API calls counter
    
    Args:
        user_id: User ID (ObjectId or string)
    """
    # Convert to string if ObjectId
    user_id_str = str(user_id)
    
    db = await get_database()
    
    await db.users.update_one(
        {"_id": ObjectId(user_id_str)},
        {"$inc": {"api_calls_count": 1}}
    )

async def update_storage_usage(user_id, size_delta: int):
    """
    Update user's storage usage
    
    Args:
        user_id: User ID (ObjectId or string)
        size_delta: Change in storage size (can be negative for deletions)
    """
    # Convert to string if ObjectId
    user_id_str = str(user_id)
    
    db = await get_database()
    
    await db.users.update_one(
        {"_id": ObjectId(user_id_str)},
        {"$inc": {"storage_used": size_delta}}
    )

def get_storage_limit_for_plan(plan: str) -> int:
    """Get storage limit in bytes for a given plan"""
    limits = {
        "free": settings.FREE_STORAGE_LIMIT,
        "starter": settings.STARTER_STORAGE_LIMIT,
        "premium": settings.PRO_STORAGE_LIMIT  # Use PRO setting for PREMIUM
    }
    return limits.get(plan.lower(), settings.FREE_STORAGE_LIMIT)