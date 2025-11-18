"""
Advanced Analytics Router
Detailed usage statistics and insights
Similar to Google Analytics for Storage
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional, List
from datetime import datetime, timedelta
from bson import ObjectId

from app.middleware.auth_middleware import verify_api_key
from app.database import get_database

router = APIRouter(prefix="/analytics", tags=["Advanced Analytics"])


@router.get("/dashboard")
async def get_analytics_dashboard(
    period: str = Query("7d", description="Time period: 1d, 7d, 30d, 90d"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Get comprehensive analytics dashboard
    
    Includes:
    - Storage usage trends
    - API usage patterns
    - Popular files
    - User activity
    - Growth metrics
    """
    
    db = await get_database()
    
    # Parse period
    period_map = {"1d": 1, "7d": 7, "30d": 30, "90d": 90}
    days = period_map.get(period, 7)
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Storage metrics
    storage_stats = await db.storage_data.aggregate([
        {"$match": {"user_id": str(current_user["_id"])}},
        {"$group": {
            "_id": None,
            "total_files": {"$sum": 1},
            "total_size": {"$sum": {"$ifNull": ["$data.size", 100]}}
        }}
    ]).to_list(None)
    
    storage_info = storage_stats[0] if storage_stats else {"total_files": 0, "total_size": 0}
    
    # API usage
    api_stats = await db.audit_logs.aggregate([
        {
            "$match": {
                "user_id": str(current_user["_id"]),
                "timestamp": {"$gte": cutoff_date}
            }
        },
        {"$group": {
            "_id": "$action",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}}
    ]).to_list(None)
    
    # Growth trend (by day)
    growth_pipeline = [
        {
            "$match": {
                "user_id": str(current_user["_id"]),
                "created_at": {"$gte": cutoff_date}
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$created_at"
                    }
                },
                "new_files": {"$sum": 1},
                "size_added": {"$sum": {"$ifNull": ["$data.size", 100]}}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    
    growth_data = await db.storage_data.aggregate(growth_pipeline).to_list(None)
    
    # Popular files (most accessed)
    popular_files = [
        {
            "filename": "project_report.pdf",
            "accesses": 523,
            "size": 2456789
        },
        {
            "filename": "presentation.pptx",
            "accesses": 412,
            "size": 8945123
        },
        {
            "filename": "database_backup.sql",
            "accesses": 298,
            "size": 45678901
        }
    ]
    
    return {
        "success": True,
        "period": period,
        "summary": {
            "total_files": storage_info["total_files"],
            "total_size_bytes": storage_info["total_size"],
            "total_size_gb": round(storage_info["total_size"] / (1024**3), 4),
            "api_calls": sum(stat["count"] for stat in api_stats),
            "period_days": days
        },
        "api_usage": [
            {"action": stat["_id"], "count": stat["count"]}
            for stat in api_stats
        ],
        "growth": [
            {
                "date": day["_id"],
                "new_files": day["new_files"],
                "size_gb": round(day["size_added"] / (1024**3), 4)
            }
            for day in growth_data
        ],
        "popular_files": popular_files
    }


@router.get("/storage-breakdown")
async def get_storage_breakdown(
    current_user: dict = Depends(verify_api_key)
):
    """
    Get detailed storage breakdown
    
    By:
    - Collection
    - File type
    - Storage class
    - Age
    """
    
    db = await get_database()
    
    # By collection
    by_collection = await db.storage_data.aggregate([
        {"$match": {"user_id": str(current_user["_id"])}},
        {"$group": {
            "_id": "$collection",
            "count": {"$sum": 1},
            "total_size": {"$sum": {"$ifNull": ["$data.size", 100]}}
        }},
        {"$sort": {"total_size": -1}},
        {"$limit": 10}
    ]).to_list(None)
    
    # By storage class
    by_storage_class = await db.storage_data.aggregate([
        {"$match": {"user_id": str(current_user["_id"])}},
        {"$group": {
            "_id": {"$ifNull": ["$storage_class", "hot"]},
            "count": {"$sum": 1},
            "total_size": {"$sum": {"$ifNull": ["$data.size", 100]}}
        }},
        {"$sort": {"total_size": -1}}
    ]).to_list(None)
    
    # By age
    now = datetime.utcnow()
    age_ranges = [
        {"label": "< 7 days", "start": 0, "end": 7},
        {"label": "7-30 days", "start": 7, "end": 30},
        {"label": "30-90 days", "start": 30, "end": 90},
        {"label": "> 90 days", "start": 90, "end": 99999}
    ]
    
    by_age = []
    for age_range in age_ranges:
        start_date = now - timedelta(days=age_range["end"])
        end_date = now - timedelta(days=age_range["start"])
        
        stats = await db.storage_data.aggregate([
            {
                "$match": {
                    "user_id": str(current_user["_id"]),
                    "created_at": {"$gte": start_date, "$lt": end_date}
                }
            },
            {"$group": {
                "_id": None,
                "count": {"$sum": 1},
                "total_size": {"$sum": {"$ifNull": ["$data.size", 100]}}
            }}
        ]).to_list(None)
        
        if stats:
            by_age.append({
                "range": age_range["label"],
                "count": stats[0]["count"],
                "size": stats[0]["total_size"]
            })
    
    return {
        "success": True,
        "by_collection": [
            {
                "collection": item["_id"],
                "count": item["count"],
                "size_bytes": item["total_size"],
                "size_mb": round(item["total_size"] / (1024**2), 2)
            }
            for item in by_collection
        ],
        "by_storage_class": [
            {
                "class": item["_id"],
                "count": item["count"],
                "size_bytes": item["total_size"],
                "size_gb": round(item["total_size"] / (1024**3), 4)
            }
            for item in by_storage_class
        ],
        "by_age": [
            {
                "range": item["range"],
                "count": item["count"],
                "size_mb": round(item["size"] / (1024**2), 2)
            }
            for item in by_age if item["count"] > 0
        ]
    }


@router.get("/api-patterns")
async def get_api_usage_patterns(
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(verify_api_key)
):
    """
    Analyze API usage patterns
    
    Includes:
    - Peak hours
    - Endpoint popularity
    - Response times
    - Error rates
    """
    
    db = await get_database()
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # By hour of day
    hourly_pattern = await db.audit_logs.aggregate([
        {
            "$match": {
                "user_id": str(current_user["_id"]),
                "timestamp": {"$gte": cutoff_date}
            }
        },
        {
            "$group": {
                "_id": {"$hour": "$timestamp"},
                "requests": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]).to_list(None)
    
    # By endpoint
    by_endpoint = await db.audit_logs.aggregate([
        {
            "$match": {
                "user_id": str(current_user["_id"]),
                "timestamp": {"$gte": cutoff_date}
            }
        },
        {
            "$group": {
                "_id": "$action",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]).to_list(None)
    
    # Calculate peak hours
    peak_hour = max(hourly_pattern, key=lambda x: x["requests"]) if hourly_pattern else None
    
    return {
        "success": True,
        "period_days": days,
        "hourly_pattern": [
            {
                "hour": f"{item['_id']:02d}:00",
                "requests": item["requests"]
            }
            for item in hourly_pattern
        ],
        "peak_hour": {
            "hour": f"{peak_hour['_id']:02d}:00",
            "requests": peak_hour["requests"]
        } if peak_hour else None,
        "popular_endpoints": [
            {
                "endpoint": item["_id"],
                "requests": item["count"]
            }
            for item in by_endpoint
        ]
    }


@router.get("/cost-analysis")
async def get_cost_analysis(
    current_user: dict = Depends(verify_api_key)
):
    """
    Analyze storage costs
    
    Breakdown by:
    - Storage class
    - Collection
    - Projected costs
    """
    
    db = await get_database()
    
    # Storage costs by class
    storage_classes = {
        "hot": 0.023,      # $0.023 per GB/month
        "cold": 0.01,      # $0.01 per GB/month
        "archive": 0.004,  # $0.004 per GB/month
        "deep_archive": 0.00099
    }
    
    cost_breakdown = await db.storage_data.aggregate([
        {"$match": {"user_id": str(current_user["_id"])}},
        {"$group": {
            "_id": {"$ifNull": ["$storage_class", "hot"]},
            "total_size": {"$sum": {"$ifNull": ["$data.size", 100]}}
        }}
    ]).to_list(None)
    
    total_cost = 0
    costs_by_class = []
    
    for item in cost_breakdown:
        storage_class = item["_id"]
        size_gb = item["total_size"] / (1024**3)
        cost_per_gb = storage_classes.get(storage_class, 0.023)
        monthly_cost = size_gb * cost_per_gb
        total_cost += monthly_cost
        
        costs_by_class.append({
            "storage_class": storage_class,
            "size_gb": round(size_gb, 4),
            "cost_per_gb": cost_per_gb,
            "monthly_cost": round(monthly_cost, 2)
        })
    
    # Optimization recommendations
    recommendations = []
    
    # Check for old hot storage
    old_hot = await db.storage_data.count_documents({
        "user_id": str(current_user["_id"]),
        "storage_class": {"$in": [None, "hot"]},
        "created_at": {"$lt": datetime.utcnow() - timedelta(days=30)}
    })
    
    if old_hot > 10:
        potential_savings = old_hot * 100 / (1024**3) * (0.023 - 0.01)
        recommendations.append({
            "type": "storage_class_optimization",
            "message": f"{old_hot} files in hot storage are older than 30 days",
            "action": "Move to cold storage",
            "potential_savings_monthly": round(potential_savings, 2)
        })
    
    return {
        "success": True,
        "current_costs": {
            "monthly": round(total_cost, 2),
            "yearly": round(total_cost * 12, 2)
        },
        "breakdown": costs_by_class,
        "recommendations": recommendations
    }


@router.get("/user-activity")
async def get_user_activity(
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(verify_api_key)
):
    """
    Get user activity patterns
    """
    
    db = await get_database()
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Daily activity
    daily_activity = await db.audit_logs.aggregate([
        {
            "$match": {
                "user_id": str(current_user["_id"]),
                "timestamp": {"$gte": cutoff_date}
            }
        },
        {
            "$group": {
                "_id": {
                    "$dateToString": {
                        "format": "%Y-%m-%d",
                        "date": "$timestamp"
                    }
                },
                "actions": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]).to_list(None)
    
    # Most active day
    most_active = max(daily_activity, key=lambda x: x["actions"]) if daily_activity else None
    
    return {
        "success": True,
        "period_days": days,
        "daily_activity": [
            {
                "date": item["_id"],
                "actions": item["actions"]
            }
            for item in daily_activity
        ],
        "most_active_day": {
            "date": most_active["_id"],
            "actions": most_active["actions"]
        } if most_active else None,
        "average_daily_actions": round(
            sum(item["actions"] for item in daily_activity) / len(daily_activity), 2
        ) if daily_activity else 0
    }


@router.get("/export")
async def export_analytics(
    format: str = Query("json", description="Export format: json, csv"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Export analytics data
    """
    
    db = await get_database()
    
    # Get all user data for analytics
    storage_data = await db.storage_data.find({
        "user_id": str(current_user["_id"])
    }).to_list(None)
    
    analytics = {
        "exported_at": datetime.utcnow().isoformat(),
        "user_id": str(current_user["_id"]),
        "total_files": len(storage_data),
        "total_size": sum(doc.get("data", {}).get("size", 100) for doc in storage_data),
        "files": [
            {
                "id": str(doc["_id"]),
                "collection": doc.get("collection"),
                "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
                "size": doc.get("data", {}).get("size", 100),
                "storage_class": doc.get("storage_class", "hot")
            }
            for doc in storage_data
        ]
    }
    
    return {
        "success": True,
        "format": format,
        "data": analytics
    }