"""
Storage Classes Router
Different storage tiers with cost optimization
Similar to AWS S3 Storage Classes
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional
from datetime import datetime
from bson import ObjectId

from app.middleware.auth_middleware import verify_api_key
from app.database import get_database

router = APIRouter(prefix="/storage-classes", tags=["Storage Classes"])

# Storage class definitions
STORAGE_CLASSES = {
    "hot": {
        "name": "Hot Storage",
        "description": "Frequently accessed data",
        "cost_per_gb": 0.023,  # $0.023 per GB/month
        "retrieval_cost": 0.0,
        "retrieval_time": "instant",
        "min_storage_days": 0
    },
    "cold": {
        "name": "Cold Storage",
        "description": "Infrequently accessed data",
        "cost_per_gb": 0.01,  # $0.01 per GB/month
        "retrieval_cost": 0.01,  # $0.01 per GB
        "retrieval_time": "minutes",
        "min_storage_days": 30
    },
    "archive": {
        "name": "Archive Storage",
        "description": "Long-term archive, rarely accessed",
        "cost_per_gb": 0.004,  # $0.004 per GB/month
        "retrieval_cost": 0.02,  # $0.02 per GB
        "retrieval_time": "hours",
        "min_storage_days": 90
    },
    "deep_archive": {
        "name": "Deep Archive",
        "description": "Lowest cost for long-term retention",
        "cost_per_gb": 0.00099,  # $0.00099 per GB/month
        "retrieval_cost": 0.0025,  # $0.0025 per GB
        "retrieval_time": "12 hours",
        "min_storage_days": 180
    }
}


@router.get("/classes")
async def list_storage_classes():
    """
    List available storage classes
    """
    
    return {
        "success": True,
        "storage_classes": STORAGE_CLASSES
    }


@router.post("/transition/{data_id}")
async def transition_storage_class(
    data_id: str,
    target_class: str = Query(..., description="hot, cold, archive, or deep_archive"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Transition data to different storage class
    
    Example:
    - hot → cold (cost savings)
    - cold → hot (faster access)
    - hot → archive (long-term storage)
    """
    
    # Validate storage class
    if target_class not in STORAGE_CLASSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid storage class. Choose from: {', '.join(STORAGE_CLASSES.keys())}"
        )
    
    db = await get_database()
    
    # Get data
    try:
        data_object_id = ObjectId(data_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data ID"
        )
    
    doc = await db.storage_data.find_one({
        "_id": data_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )
    
    current_class = doc.get("storage_class", "hot")
    
    # Update storage class
    await db.storage_data.update_one(
        {"_id": data_object_id},
        {
            "$set": {
                "storage_class": target_class,
                "previous_storage_class": current_class,
                "transitioned_at": datetime.utcnow()
            },
            "$push": {
                "transition_history": {
                    "from": current_class,
                    "to": target_class,
                    "timestamp": datetime.utcnow()
                }
            }
        }
    )
    
    return {
        "success": True,
        "data_id": data_id,
        "from_class": current_class,
        "to_class": target_class,
        "message": f"Data transitioned from {current_class} to {target_class}"
    }


@router.get("/analyze")
async def analyze_storage_usage(
    current_user: dict = Depends(verify_api_key)
):
    """
    Analyze storage usage by storage class
    Provides cost optimization recommendations
    """
    
    db = await get_database()
    
    # Aggregate by storage class
    pipeline = [
        {"$match": {"user_id": str(current_user["_id"])}},
        {"$group": {
            "_id": {"$ifNull": ["$storage_class", "hot"]},
            "count": {"$sum": 1},
            "total_size": {"$sum": {"$ifNull": ["$data.size", 100]}}  # Default 100 bytes
        }}
    ]
    
    result = await db.storage_data.aggregate(pipeline).to_list(None)
    
    # Calculate costs
    usage_by_class = {}
    total_cost = 0
    total_size = 0
    
    for item in result:
        storage_class = item["_id"]
        count = item["count"]
        size_bytes = item["total_size"]
        size_gb = size_bytes / (1024 ** 3)
        
        class_info = STORAGE_CLASSES.get(storage_class, STORAGE_CLASSES["hot"])
        monthly_cost = size_gb * class_info["cost_per_gb"]
        
        usage_by_class[storage_class] = {
            "count": count,
            "size_bytes": size_bytes,
            "size_gb": round(size_gb, 4),
            "monthly_cost": round(monthly_cost, 2),
            "class_info": class_info
        }
        
        total_cost += monthly_cost
        total_size += size_bytes
    
    # Generate recommendations
    recommendations = []
    
    # Check for hot storage candidates for transition
    hot_data = await db.storage_data.find({
        "user_id": str(current_user["_id"]),
        "storage_class": {"$in": [None, "hot"]},
        "created_at": {"$lt": datetime.utcnow() - timedelta(days=30)}
    }).limit(100).to_list(None)
    
    if len(hot_data) > 10:
        potential_savings = len(hot_data) * 100 / (1024**3) * (0.023 - 0.01)  # Rough estimate
        recommendations.append({
            "type": "transition_to_cold",
            "message": f"{len(hot_data)} files in hot storage haven't been accessed in 30 days",
            "action": "Consider transitioning to cold storage",
            "potential_savings": round(potential_savings, 2)
        })
    
    return {
        "success": True,
        "usage_by_class": usage_by_class,
        "total": {
            "size_bytes": total_size,
            "size_gb": round(total_size / (1024 ** 3), 4),
            "monthly_cost": round(total_cost, 2)
        },
        "recommendations": recommendations
    }


@router.get("/costs")
async def calculate_storage_costs(
    size_gb: float = Query(..., description="Size in GB"),
    storage_class: str = Query("hot", description="Storage class")
):
    """
    Calculate storage costs for given size and class
    """
    
    if storage_class not in STORAGE_CLASSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid storage class. Choose from: {', '.join(STORAGE_CLASSES.keys())}"
        )
    
    class_info = STORAGE_CLASSES[storage_class]
    
    monthly_cost = size_gb * class_info["cost_per_gb"]
    yearly_cost = monthly_cost * 12
    
    # Calculate costs for all classes for comparison
    comparison = {}
    for sc_name, sc_info in STORAGE_CLASSES.items():
        comparison[sc_name] = {
            "monthly": round(size_gb * sc_info["cost_per_gb"], 2),
            "yearly": round(size_gb * sc_info["cost_per_gb"] * 12, 2)
        }
    
    return {
        "success": True,
        "size_gb": size_gb,
        "storage_class": storage_class,
        "monthly_cost": round(monthly_cost, 2),
        "yearly_cost": round(yearly_cost, 2),
        "class_info": class_info,
        "comparison": comparison
    }


@router.post("/bulk-transition")
async def bulk_transition_storage_class(
    collection: Optional[str] = None,
    target_class: str = Query(...),
    older_than_days: int = Query(30, description="Only transition files older than X days"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Bulk transition multiple files to different storage class
    """
    
    if target_class not in STORAGE_CLASSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid storage class"
        )
    
    db = await get_database()
    
    # Build query
    query = {
        "user_id": str(current_user["_id"]),
        "created_at": {"$lt": datetime.utcnow() - timedelta(days=older_than_days)}
    }
    
    if collection:
        query["collection"] = collection
    
    # Update documents
    result = await db.storage_data.update_many(
        query,
        {
            "$set": {
                "storage_class": target_class,
                "transitioned_at": datetime.utcnow()
            }
        }
    )
    
    return {
        "success": True,
        "affected": result.modified_count,
        "target_class": target_class,
        "message": f"Transitioned {result.modified_count} files to {target_class}"
    }


from datetime import timedelta

@router.get("/history/{data_id}")
async def get_transition_history(
    data_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get storage class transition history for a file
    """
    
    db = await get_database()
    
    try:
        data_object_id = ObjectId(data_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data ID"
        )
    
    doc = await db.storage_data.find_one({
        "_id": data_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )
    
    current_class = doc.get("storage_class", "hot")
    transition_history = doc.get("transition_history", [])
    
    # Format history
    formatted_history = []
    for transition in transition_history:
        formatted_history.append({
            "from": transition["from"],
            "to": transition["to"],
            "timestamp": transition["timestamp"].isoformat()
        })
    
    return {
        "success": True,
        "data_id": data_id,
        "current_class": current_class,
        "history": formatted_history
    }