"""
Search Router
Full-text search functionality using MongoDB regex
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
    - Searches across specified fields or all string fields
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

        # DEBUG: Log parsed fields
        import logging
        logging.info(f"Raw fields parameter: {fields}")
        logging.info(f"Parsed search_fields: {search_fields}")
        logging.info(f"[SEARCH] User ID: {current_user['_id']}")

        # Build base query
        base_query = {
            "collection": collection,
            "user_id": str(current_user["_id"])  # ← 수정!
        }

        # DEBUG: Check if any documents exist
        total_in_collection = await db.storage_data.count_documents(base_query)
        logging.info(f"Total documents in collection '{collection}' for this user: {total_in_collection}")

        # Build search conditions
        or_conditions = []

        logging.info(f"Building search with search_fields: {search_fields}")

        if search_fields:
            # Search specific fields
            logging.info(f"Using specific fields: {search_fields}")
            for field in search_fields:
                or_conditions.append({
                    f"data.{field}": {"$regex": query, "$options": "i"}
                })
        else:
            # Search all fields - get all documents and filter in Python
            logging.info("No specific fields, sampling documents...")
            all_docs = await db.storage_data.find(base_query).to_list(length=1000)
    
            # Find which fields contain strings (sample more documents)
            string_fields = set()
            sample_size = min(len(all_docs), 100)  # Sample up to 100 docs
            for doc in all_docs[:sample_size]:
                if "data" in doc:
                    for key, value in doc["data"].items():
                        if isinstance(value, str):
                            string_fields.add(key)
    
           # Build OR query for all string fields
            for field in string_fields:
                or_conditions.append({
                    f"data.{field}": {"$regex": query, "$options": "i"}
                })
        
        # Add OR conditions to base query
        if or_conditions:
            base_query["$or"] = or_conditions
        else:
            # No string fields found, return empty
            await increment_api_calls(current_user["_id"])
            return {
                "success": True,
                "query": query,
                "collection": collection,
                "fields": search_fields or ["all"],
                "results": [],
                "total": 0,
                "limit": limit,
                "skip": skip
            }
        
        # DEBUG: Log the query
        import logging
        logging.info(f"Search query: {base_query}")
        logging.info(f"OR conditions: {or_conditions}")
        
        # DEBUG: Check if any documents exist at all
        total_in_collection = await db.storage_data.count_documents({
            "collection": collection,
            "user_id": current_user["_id"]
        })
        logging.info(f"Total documents in collection '{collection}' for this user: {total_in_collection}")
        
        # DEBUG: Try finding without OR conditions
        test_query = {
            "collection": collection,
            "user_id": current_user["_id"]
        }
        test_results = await db.storage_data.find(test_query).limit(3).to_list(length=3)
        logging.info(f"Sample documents (first 3):")
        for doc in test_results:
            logging.info(f"  - {doc.get('data', {})}")
        
        # Execute search with pagination
        cursor = db.storage_data.find(base_query).skip(skip).limit(limit)
        results = await cursor.to_list(length=limit)
        
        # Get total count
        total = await db.storage_data.count_documents(base_query)
        
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
            "fields": search_fields or list(string_fields) if not search_fields and 'string_fields' in locals() else ["all"],
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
    collection: str = Query(...),
    field: str = Query(...),
    prefix: str = Query(..., min_length=1),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(verify_api_key)
):
    # ...
    
    # Build query
    query = {
        "collection": collection,
        "user_id": str(current_user["_id"]),  # ← 이 부분 수정!
        f"data.{field}": {"$regex": f"^{re.escape(prefix)}", "$options": "i"}
    }
    
    # Check API calls quota
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        
        # Build query with case-insensitive prefix match
        query = {
            "collection": collection,
            "user_id": current_user["_id"],
            f"data.{field}": {"$regex": f"^{re.escape(prefix)}", "$options": "i"}
        }
        
        # Get matching documents
        cursor = db.storage_data.find(
            query,
            {f"data.{field}": 1}
        ).limit(limit * 2)  # Get more to account for duplicates
        
        docs = await cursor.to_list(length=limit * 2)
        
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
                        
                        if len(suggestions) >= limit:
                            break
            except:
                continue
        
        # Increment API calls
        await increment_api_calls(current_user["_id"])
        
        return {
            "success": True,
            "field": field,
            "prefix": prefix,
            "suggestions": suggestions,
            "count": len(suggestions)
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Autocomplete failed: {str(e)}"
        )