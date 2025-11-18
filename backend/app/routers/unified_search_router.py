"""
Unified Search Router
Searches across both V1 (MongoDB) and V2 (R2) storage
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import List, Optional
from bson import ObjectId
from datetime import datetime
import logging

from app.middleware.auth_middleware import verify_api_key
from app.database import get_database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/unified-search", tags=["Unified Search"])


@router.get("")
async def unified_search(
    q: str = Query(..., description="Search query", min_length=1),
    collection: Optional[str] = Query(None, description="Filter by collection"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    include_v1: bool = Query(True, description="Include V1 (MongoDB) results"),
    include_v2: bool = Query(True, description="Include V2 (R2) results"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Unified search across V1 and V2 storage
    
    Searches:
    - V1: MongoDB text index search
    - V2: Collection and metadata search
    
    Returns combined results sorted by relevance
    """
    
    db = await get_database()
    all_results = []
    
    # ========================================
    # V1 Search (MongoDB storage_data)
    # ========================================
    if include_v1:
        try:
            # Build V1 query
            v1_query = {
                "user_id": str(current_user["_id"]),
                "$text": {"$search": q}
            }
            
            if collection:
                v1_query["collection"] = collection
            
            # Execute V1 search
            v1_cursor = db.storage_data.find(
                v1_query,
                {"score": {"$meta": "textScore"}}
            ).sort([("score", {"$meta": "textScore"})]).limit(limit)
            
            v1_results = await v1_cursor.to_list(length=limit)
            
            # Format V1 results
            for doc in v1_results:
                all_results.append({
                    "id": str(doc["_id"]),
                    "collection": doc.get("collection"),
                    "data": doc.get("data"),
                    "storage_type": doc.get("storage_type", "mongodb"),
                    "api_version": "v1",
                    "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
                    "score": doc.get("score", 0),
                    "source": "v1_storage"
                })
                
            logger.info(f"V1 search found {len(v1_results)} results for '{q}'")
            
        except Exception as e:
            logger.error(f"V1 search error: {e}")
            # Continue to V2 search even if V1 fails
    
    # ========================================
    # V2 Search (Cloudflare R2)
    # ========================================
    if include_v2:
        try:
            # Build V2 query - search in collection and tags
            v2_query = {
                "user_id": str(current_user["_id"])
            }
            
            if collection:
                v2_query["collection"] = collection
            
            # Search in collection name, tags, or use text search if available
            v2_search_conditions = []
            
            # Search in collection name
            v2_search_conditions.append({"collection": {"$regex": q, "$options": "i"}})
            
            # Search in tags
            v2_search_conditions.append({"tags": {"$regex": q, "$options": "i"}})
            
            # Search in data fields (if data is stored as subdocument)
            v2_search_conditions.append({"data": {"$regex": q, "$options": "i"}})
            
            if v2_search_conditions:
                v2_query["$or"] = v2_search_conditions
            
            # Execute V2 search
            v2_cursor = db.storage_data.find(v2_query).sort("created_at", -1).limit(limit)
            v2_results = await v2_cursor.to_list(length=limit)
            
            # Format V2 results
            for doc in v2_results:
                all_results.append({
                    "id": str(doc["_id"]),
                    "collection": doc.get("collection"),
                    "data": doc.get("data"),
                    "tags": doc.get("tags", []),
                    "metadata": doc.get("metadata", {}),
                    "storage_type": doc.get("storage_type", "mongodb"),
                    "api_version": "v2",
                    "version": doc.get("version", 1),
                    "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None,
                    "score": 1.0,  # Default score for V2
                    "source": "v2_storage"
                })
                
            logger.info(f"V2 search found {len(v2_results)} results for '{q}'")
            
        except Exception as e:
            logger.error(f"V2 search error: {e}")
    
    # ========================================
    # Combine and sort results
    # ========================================
    
    # Sort by score (descending) and then by created_at (newest first)
    all_results.sort(key=lambda x: (-x.get("score", 0), x.get("created_at", "")), reverse=True)
    
    # Limit total results
    all_results = all_results[:limit]
    
    return {
        "success": True,
        "query": q,
        "total": len(all_results),
        "results": all_results,
        "sources": {
            "v1_included": include_v1,
            "v2_included": include_v2
        },
        "metadata": {
            "limit": limit,
            "collection_filter": collection,
            "timestamp": datetime.utcnow().isoformat()
        }
    }


@router.get("/stats")
async def search_stats(
    current_user: dict = Depends(verify_api_key)
):
    """
    Get search statistics
    
    Returns:
    - Total items in V1
    - Total items in V2
    - Collections available
    """
    
    db = await get_database()
    
    # Count V1 items
    v1_count = await db.storage_data.count_documents({
        "user_id": str(current_user["_id"]),
        "$or": [
            {"storage_type": "mongodb"},
            {"storage_type": {"$exists": False}}  # Old documents without storage_type
        ]
    })
    
    # Count V2 items
    v2_count = await db.storage_data.count_documents({
        "user_id": str(current_user["_id"]),
        "version": {"$exists": True}  # V2 documents have version field
    })
    
    # Get all collections
    pipeline = [
        {"$match": {"user_id": str(current_user["_id"])}},
        {"$group": {"_id": "$collection"}},
        {"$sort": {"_id": 1}}
    ]
    
    collections_cursor = db.storage_data.aggregate(pipeline)
    collections = [doc["_id"] for doc in await collections_cursor.to_list(None) if doc["_id"]]
    
    return {
        "success": True,
        "v1_items": v1_count,
        "v2_items": v2_count,
        "total_items": v1_count + v2_count,
        "collections": collections,
        "collections_count": len(collections)
    }