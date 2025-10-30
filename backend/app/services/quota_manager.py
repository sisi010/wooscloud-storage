"""
Quota management service
Handles storage limits and API rate limits
"""
from fastapi import HTTPException
from app.database import get_database
from app.config import settings

async def check_storage_quota(user_id: str, additional_size: int):
    """
    Check if user has enough storage quota
    
    Args:
        user_id: User ID
        additional_size: Size of new data in bytes
    
    Raises:
        HTTPException: If quota exceeded
    """
    db = await get_database()
    user = await db.users.find_one({"_id": user_id})
    
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

async def check_api_calls_quota(user_id: str):
    """
    Check if user has API calls remaining
    
    Args:
        user_id: User ID
    
    Raises:
        HTTPException: If quota exceeded
    """
    db = await get_database()
    user = await db.users.find_one({"_id": user_id})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # PRO and STARTER plans have unlimited API calls
    if user.get("plan") in ["starter", "pro"]:
        return
    
    api_calls_count = user.get("api_calls_count", 0)
    api_calls_limit = user.get("api_calls_limit", settings.FREE_API_CALLS_LIMIT)
    
    if api_calls_count >= api_calls_limit:
        raise HTTPException(
            status_code=429,
            detail={
                "error": "API calls limit exceeded",
                "message": "You've reached your monthly API calls limit. Please upgrade to STARTER or PRO for unlimited calls.",
                "current_usage": api_calls_count,
                "limit": api_calls_limit,
                "upgrade_url": "https://woos-ai.com/pricing.html"
            }
        )

async def increment_api_calls(user_id: str):
    """Increment user's API calls counter"""
    db = await get_database()
    
    await db.users.update_one(
        {"_id": user_id},
        {"$inc": {"api_calls_count": 1}}
    )

async def update_storage_usage(user_id: str, size_delta: int):
    """
    Update user's storage usage
    
    Args:
        user_id: User ID
        size_delta: Change in storage size (can be negative for deletions)
    """
    db = await get_database()
    
    await db.users.update_one(
        {"_id": user_id},
        {"$inc": {"storage_used": size_delta}}
    )

def get_storage_limit_for_plan(plan: str) -> int:
    """Get storage limit in bytes for a given plan"""
    limits = {
        "free": settings.FREE_STORAGE_LIMIT,
        "starter": settings.STARTER_STORAGE_LIMIT,
        "pro": settings.PRO_STORAGE_LIMIT
    }
    return limits.get(plan, settings.FREE_STORAGE_LIMIT)