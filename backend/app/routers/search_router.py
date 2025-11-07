"""
Search Router
Full-text search functionality using MongoDB text indexes
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from app.middleware.auth_middleware import verify_api_key
from app.database import get_database
from app.services.quota_manager import check_api_calls_quota, increment_api_calls
from bson import ObjectId
import re

router = APIRouter()

@router.get("/search")
async def search_data(
    collection: str = Query(..., description="Collection to search"),
    query: str = Query(..., description="Search query"),
    fields: Optional[str] = Query(None, description="Comma-separated fields to search (e.g., 'name,description')"),
    limit: int = Query(10, ge=1, le=100),
    skip: int = Query(0, ge=0),
    current_user: dict = Depends(verify_api_key)
):
    """
    Full-text search in a collection
    
    Features:
    - Searches across specified fields or all text fields
    - Case-insensitive
    - Partial matching
    - Korean and emoji support
    
    Example:
        GET /api/search?collection=products&query=laptop&fields=name,description&limit=10
    """
    
    # Check API calls quota
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        
        # Parse fields
        search_fields = []
        if fields:
            search_fields = [f.strip() for f in fields.split(",")]
        
        # Build search query
        search_query = {
            "collection": collection,
            "user_id": current_user["_id"]
        }
        
        # Create regex pattern for partial matching (case-insensitive)
        pattern = re.compile(re.escape(query), re.IGNORECASE)
        
        # Build OR query for multiple fields
        if search_fields:
            or_conditions = []
            for field in search_fields:
                or_conditions.append({f"data.{field}": pattern})
            search_query["$or"] = or_conditions
        else:
            # Search all fields in data (fallback)
            # Get a sample document to determine fields
            sample = await db.storage_data.find_one({
                "collection": collection,
                "user_id": current_user["_id"]
            })
            
            if sample and "data" in sample:
                # Search all string fields in data
                or_conditions = []
                for key, value in sample["data"].items():
                    if isinstance(value, str):
                        or_conditions.append({f"data.{key}": pattern})
                
                if or_conditions:
                    search_query["$or"] = or_conditions
                else:
                    # No string fields found, return empty
                    search_query["_id"] = None  # Match nothing
        
        # Execute search
        cursor = db.storage_data.find(search_query).skip(skip).limit(limit)
        results = await cursor.to_list(length=limit)
        
        # Get total count
        total = await db.storage_data.count_documents(search_query)
        
        # Format results
        formatted_results = []
        for doc in results:
            formatted_results.append({
                "id": str(doc["_id"]),
                "collection": doc["collection"],
                "data": doc["data"],
                "storage_type": doc.get("storage_type", "mongodb"),
                "created_at": doc["created_at"].isoformat() if doc.get("created_at") else None,
                "updated_at": doc["updated_at"].isoformat() if doc.get("updated_at") else None
            })
        
        # Increment API calls
        await increment_api_calls(current_user["_id"])
        
        return {
            "success": True,
            "query": query,
            "collection": collection,
            "fields": search_fields or ["all"],
            "results": formatted_results,
            "total": total,
            "limit": limit,
            "skip": skip
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Search failed: {str(e)}"
        )

@router.get("/autocomplete")
async def autocomplete(
    collection: str = Query(..., description="Collection to search"),
    field: str = Query(..., description="Field to search (e.g., 'name')"),
    prefix: str = Query(..., description="Prefix to match", min_length=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(verify_api_key)
):
    """
    Autocomplete suggestions
    
    Returns unique values that start with the given prefix
    
    Example:
        GET /api/autocomplete?collection=products&field=name&prefix=lap&limit=10
        Returns: ["Laptop HP", "Laptop Dell", "Laptop Asus", ...]
    """
    
    # Check API calls quota
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        
        # Build query
        query = {
            "collection": collection,
            "user_id": current_user["_id"],
            f"data.{field}": {"$regex": f"^{re.escape(prefix)}", "$options": "i"}
        }
        
        # Get distinct values
        cursor = db.storage_data.find(
            query,
            {f"data.{field}": 1}
        ).limit(limit)
        
        docs = await cursor.to_list(length=limit)
        
        # Extract unique suggestions
        suggestions = []
        seen = set()
        
        for doc in docs:
            try:
                # Navigate nested field path
                value = doc["data"]
                for part in field.split("."):
                    value = value.get(part)
                    if value is None:
                        break
                
                if value and isinstance(value, str):
                    if value.lower() not in seen:
                        suggestions.append(value)
                        seen.add(value.lower())
            except:
                continue
        
        # Increment API calls
        await increment_api_calls(current_user["_id"])
        
        return {
            "success": True,
            "field": field,
            "prefix": prefix,
            "suggestions": suggestions[:limit],
            "count": len(suggestions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Autocomplete failed: {str(e)}"
        )

@router.post("/search/create-index")
async def create_search_index(
    collection: str = Query(..., description="Collection name"),
    fields: List[str] = Query(..., description="Fields to index"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Create text search index for a collection
    
    Admin/Owner only feature
    Creates MongoDB text index for specified fields
    
    Example:
        POST /api/search/create-index?collection=products&fields=name&fields=description
    """
    
    # Check API calls quota
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        
        # Build index specification
        index_spec = []
        for field in fields:
            index_spec.append((f"data.{field}", "text"))
        
        # Create index
        index_name = await db.storage_data.create_index(
            index_spec,
            name=f"search_{collection}_{'_'.join(fields)}"
        )
        
        # Increment API calls
        await increment_api_calls(current_user["_id"])
        
        return {
            "success": True,
            "message": "Search index created",
            "index_name": index_name,
            "collection": collection,
            "fields": fields
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create index: {str(e)}"
        )