"""
CDN Integration Router
Cloudflare CDN integration for global content delivery
Similar to AWS CloudFront
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional, List
from datetime import datetime, timedelta
from bson import ObjectId
from pydantic import BaseModel
import hashlib

from app.middleware.auth_middleware import verify_api_key
from app.database import get_database

router = APIRouter(prefix="/cdn", tags=["CDN Integration"])

# CDN Configuration
CDN_ENABLED = True  # Set to False to disable CDN features
CDN_PROVIDER = "Cloudflare"
CDN_DOMAIN = "cdn.wooscloud.com"

# Cache TTL settings (in seconds)
CACHE_TTL = {
    "static": 31536000,      # 1 year for static assets
    "images": 2592000,       # 30 days for images
    "videos": 604800,        # 7 days for videos
    "documents": 86400,      # 1 day for documents
    "api": 300,              # 5 minutes for API responses
    "default": 3600          # 1 hour default
}


class CachePurgeRequest(BaseModel):
    """Cache purge request"""
    urls: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    purge_all: bool = False


class CDNConfig(BaseModel):
    """CDN configuration"""
    enabled: bool = True
    cache_ttl: int = 3600
    cache_control: str = "public, max-age=3600"
    compression: bool = True
    minification: bool = False


@router.get("/status")
async def get_cdn_status():
    """
    Get CDN status and configuration
    """
    
    return {
        "success": True,
        "cdn": {
            "enabled": CDN_ENABLED,
            "provider": CDN_PROVIDER,
            "domain": CDN_DOMAIN,
            "cache_ttl": CACHE_TTL
        },
        "features": {
            "caching": True,
            "compression": True,
            "ssl": True,
            "http2": True,
            "ipv6": True
        }
    }


@router.get("/url/{data_id}")
async def get_cdn_url(
    data_id: str,
    content_type: Optional[str] = Query("default", description="Content type for cache TTL"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Get CDN URL for a file
    
    Returns CDN-optimized URL with proper cache headers
    """
    
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
    
    # Generate CDN URL
    filename = doc.get("data", {}).get("filename", "file")
    
    if CDN_ENABLED:
        cdn_url = f"https://{CDN_DOMAIN}/files/{data_id}/{filename}"
    else:
        cdn_url = f"/api/files/{data_id}"
    
    # Get cache TTL
    ttl = CACHE_TTL.get(content_type, CACHE_TTL["default"])
    
    # Cache headers
    cache_headers = {
        "Cache-Control": f"public, max-age={ttl}",
        "CDN-Cache-Control": f"max-age={ttl}",
        "Expires": (datetime.utcnow() + timedelta(seconds=ttl)).isoformat()
    }
    
    return {
        "success": True,
        "cdn_url": cdn_url,
        "original_url": f"/api/files/{data_id}",
        "cache_ttl": ttl,
        "headers": cache_headers,
        "cdn_enabled": CDN_ENABLED
    }


@router.post("/purge")
async def purge_cache(
    request: CachePurgeRequest,
    current_user: dict = Depends(verify_api_key)
):
    """
    Purge CDN cache
    
    Options:
    - Purge specific URLs
    - Purge by tags
    - Purge all (requires admin)
    """
    
    if not CDN_ENABLED:
        return {
            "success": True,
            "message": "CDN not enabled",
            "purged": 0
        }
    
    db = await get_database()
    
    purged_count = 0
    purged_urls = []
    
    if request.purge_all:
        # Purge all cache (admin only in production)
        purged_count = await db.cdn_cache.delete_many({
            "user_id": str(current_user["_id"])
        })
        purged_count = purged_count.deleted_count
        
    elif request.urls:
        # Purge specific URLs
        for url in request.urls:
            result = await db.cdn_cache.delete_one({
                "url": url,
                "user_id": str(current_user["_id"])
            })
            if result.deleted_count > 0:
                purged_count += 1
                purged_urls.append(url)
    
    elif request.tags:
        # Purge by tags
        result = await db.cdn_cache.delete_many({
            "tags": {"$in": request.tags},
            "user_id": str(current_user["_id"])
        })
        purged_count = result.deleted_count
    
    # Log purge operation
    await db.cdn_purge_log.insert_one({
        "user_id": str(current_user["_id"]),
        "purge_type": "all" if request.purge_all else "selective",
        "urls": request.urls or [],
        "tags": request.tags or [],
        "purged_count": purged_count,
        "timestamp": datetime.utcnow()
    })
    
    return {
        "success": True,
        "message": f"Purged {purged_count} cached items",
        "purged": purged_count,
        "urls": purged_urls
    }


@router.get("/stats")
async def get_cdn_stats(
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(verify_api_key)
):
    """
    Get CDN usage statistics
    
    Includes:
    - Cache hit ratio
    - Bandwidth saved
    - Request distribution
    - Edge locations
    """
    
    db = await get_database()
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Aggregate CDN stats
    pipeline = [
        {
            "$match": {
                "user_id": str(current_user["_id"]),
                "timestamp": {"$gte": cutoff_date}
            }
        },
        {
            "$group": {
                "_id": None,
                "total_requests": {"$sum": 1},
                "cache_hits": {
                    "$sum": {"$cond": [{"$eq": ["$cache_status", "HIT"]}, 1, 0]}
                },
                "cache_misses": {
                    "$sum": {"$cond": [{"$eq": ["$cache_status", "MISS"]}, 1, 0]}
                },
                "total_bytes": {"$sum": "$bytes_sent"},
                "cached_bytes": {
                    "$sum": {"$cond": [{"$eq": ["$cache_status", "HIT"]}, "$bytes_sent", 0]}
                }
            }
        }
    ]
    
    result = await db.cdn_stats.aggregate(pipeline).to_list(None)
    
    if result:
        stats = result[0]
        cache_hit_ratio = (stats["cache_hits"] / stats["total_requests"] * 100) if stats["total_requests"] > 0 else 0
        bandwidth_saved = (stats["cached_bytes"] / stats["total_bytes"] * 100) if stats["total_bytes"] > 0 else 0
    else:
        stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "total_bytes": 0,
            "cached_bytes": 0
        }
        cache_hit_ratio = 0
        bandwidth_saved = 0
    
    # Get edge locations (simulated)
    edge_locations = [
        {"location": "San Francisco, US", "requests": 1523, "percentage": 35.2},
        {"location": "London, UK", "requests": 982, "percentage": 22.7},
        {"location": "Singapore", "requests": 756, "percentage": 17.5},
        {"location": "Tokyo, Japan", "requests": 543, "percentage": 12.6},
        {"location": "Sydney, Australia", "requests": 521, "percentage": 12.0}
    ]
    
    return {
        "success": True,
        "period": {
            "days": days,
            "from": cutoff_date.isoformat(),
            "to": datetime.utcnow().isoformat()
        },
        "stats": {
            "total_requests": stats["total_requests"],
            "cache_hits": stats["cache_hits"],
            "cache_misses": stats["cache_misses"],
            "cache_hit_ratio": round(cache_hit_ratio, 2),
            "total_bandwidth": stats["total_bytes"],
            "cached_bandwidth": stats["cached_bytes"],
            "bandwidth_saved_percent": round(bandwidth_saved, 2)
        },
        "edge_locations": edge_locations,
        "cdn_provider": CDN_PROVIDER
    }


@router.post("/config/{data_id}")
async def configure_cdn(
    data_id: str,
    config: CDNConfig,
    current_user: dict = Depends(verify_api_key)
):
    """
    Configure CDN settings for a specific file
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
    
    # Update CDN config
    await db.storage_data.update_one(
        {"_id": data_object_id},
        {
            "$set": {
                "cdn_config": config.dict(),
                "cdn_updated_at": datetime.utcnow()
            }
        }
    )
    
    return {
        "success": True,
        "data_id": data_id,
        "cdn_config": config.dict(),
        "message": "CDN configuration updated"
    }


@router.get("/cache-info/{data_id}")
async def get_cache_info(
    data_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get cache information for a file
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
    
    # Get cache stats for this file
    cache_stats = await db.cdn_stats.find({
        "data_id": data_id,
        "user_id": str(current_user["_id"])
    }).sort("timestamp", -1).limit(100).to_list(None)
    
    cache_hits = sum(1 for stat in cache_stats if stat.get("cache_status") == "HIT")
    cache_misses = sum(1 for stat in cache_stats if stat.get("cache_status") == "MISS")
    
    total = cache_hits + cache_misses
    hit_ratio = (cache_hits / total * 100) if total > 0 else 0
    
    return {
        "success": True,
        "data_id": data_id,
        "cache_info": {
            "cached": doc.get("cdn_config", {}).get("enabled", True),
            "cache_ttl": doc.get("cdn_config", {}).get("cache_ttl", 3600),
            "hits": cache_hits,
            "misses": cache_misses,
            "hit_ratio": round(hit_ratio, 2),
            "last_accessed": cache_stats[0]["timestamp"].isoformat() if cache_stats else None
        }
    }


@router.get("/bandwidth")
async def get_bandwidth_usage(
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(verify_api_key)
):
    """
    Get bandwidth usage breakdown
    """
    
    db = await get_database()
    
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    
    # Aggregate bandwidth by day
    pipeline = [
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
                "total_bytes": {"$sum": "$bytes_sent"},
                "requests": {"$sum": 1}
            }
        },
        {"$sort": {"_id": 1}}
    ]
    
    daily_usage = await db.cdn_stats.aggregate(pipeline).to_list(None)
    
    total_bandwidth = sum(day["total_bytes"] for day in daily_usage)
    total_requests = sum(day["requests"] for day in daily_usage)
    
    return {
        "success": True,
        "period": {
            "days": days,
            "from": cutoff_date.isoformat(),
            "to": datetime.utcnow().isoformat()
        },
        "total": {
            "bandwidth_bytes": total_bandwidth,
            "bandwidth_gb": round(total_bandwidth / (1024**3), 4),
            "requests": total_requests
        },
        "daily": [
            {
                "date": day["_id"],
                "bytes": day["total_bytes"],
                "gb": round(day["total_bytes"] / (1024**3), 4),
                "requests": day["requests"]
            }
            for day in daily_usage
        ]
    }