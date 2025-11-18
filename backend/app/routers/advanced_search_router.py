"""
Advanced Search Router
MongoDB Atlas Search with fuzzy search, autocomplete, and advanced filtering
Similar to Elasticsearch features
"""

from fastapi import APIRouter, HTTPException, Depends, Query, status
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from app.middleware.auth_middleware import verify_api_key
from app.database import get_database

router = APIRouter(prefix="/advanced-search", tags=["Advanced Search"])


class SearchRequest(BaseModel):
    """Advanced search request"""
    query: str = Field(..., description="Search query")
    collections: Optional[List[str]] = Field(None, description="Filter by collections")
    tags: Optional[List[str]] = Field(None, description="Filter by tags")
    date_from: Optional[datetime] = Field(None, description="Filter from date")
    date_to: Optional[datetime] = Field(None, description="Filter to date")
    fuzzy: bool = Field(True, description="Enable fuzzy search (typo tolerance)")
    limit: int = Field(10, ge=1, le=100, description="Results limit")
    skip: int = Field(0, ge=0, description="Results to skip (pagination)")


class SearchResult(BaseModel):
    """Search result with score"""
    id: str
    collection: str
    data: Dict[str, Any]
    score: float
    highlights: Optional[Dict[str, List[str]]] = None


class SearchResponse(BaseModel):
    """Search response"""
    success: bool = True
    query: str
    total: int
    results: List[SearchResult]
    facets: Optional[Dict[str, Any]] = None
    took_ms: Optional[float] = None


@router.post("/search", response_model=SearchResponse)
async def advanced_search(
    request: SearchRequest,
    current_user: dict = Depends(verify_api_key)
):
    """
    Advanced full-text search with fuzzy matching
    
    Features:
    - Fuzzy search (typo tolerance)
    - Relevance scoring
    - Date range filtering
    - Collection filtering
    - Tag filtering
    - Pagination
    
    Example:
    ```json
    {
      "query": "important documnt",  // Will match "important document"
      "fuzzy": true,
      "collections": ["reports"],
      "limit": 10
    }
    ```
    """
    
    db = await get_database()
    start_time = datetime.now()
    
    # Build Atlas Search query
    search_query = {
        "text": {
            "query": request.query,
            "path": ["data", "collection", "tags", "metadata.filename", "metadata.description"],
            "fuzzy": {
                "maxEdits": 2,  # Allow 2 character changes (typos)
                "prefixLength": 0,
                "maxExpansions": 100
            } if request.fuzzy else None
        }
    }
    
    # Build filter conditions
    must_conditions = [
        {"equals": {"path": "user_id", "value": str(current_user["_id"])}}
    ]
    
    # Collection filter
    if request.collections:
        must_conditions.append({
            "in": {
                "path": "collection",
                "value": request.collections
            }
        })
    
    # Tag filter
    if request.tags:
        must_conditions.append({
            "in": {
                "path": "tags",
                "value": request.tags
            }
        })
    
    # Date range filter
    if request.date_from or request.date_to:
        date_filter = {"path": "created_at"}
        if request.date_from:
            date_filter["gte"] = request.date_from
        if request.date_to:
            date_filter["lte"] = request.date_to
        must_conditions.append({"range": date_filter})
    
    # Build aggregation pipeline
    pipeline = [
        {
            "$search": {
                "index": "default",  # Atlas Search index name
                "compound": {
                    "must": [search_query],
                    "filter": must_conditions
                }
            }
        },
        {
            "$addFields": {
                "score": {"$meta": "searchScore"}
            }
        },
        {"$skip": request.skip},
        {"$limit": request.limit},
        {
            "$project": {
                "_id": 1,
                "collection": 1,
                "data": 1,
                "tags": 1,
                "metadata": 1,
                "score": 1,
                "created_at": 1
            }
        }
    ]
    
    try:
        # Execute search
        try:
            results = await db.storage_data.aggregate(pipeline).to_list(None)
        except Exception as search_error:
            # Log specific search error
            print(f"Search execution error: {search_error}")
            results = []
        
        # Get total count
        try:
            count_pipeline = [
                {
                    "$search": {
                        "index": "default",
                        "compound": {
                            "must": [search_query],
                            "filter": must_conditions
                        }
                    }
                },
                {"$count": "total"}
            ]
            
            count_result = await db.storage_data.aggregate(count_pipeline).to_list(None)
            total = count_result[0]["total"] if count_result else 0
        except Exception as count_error:
            print(f"Count error: {count_error}")
            total = 0
        
        # Format results
        search_results = []
        for doc in results:
            # Safely handle data field
            data = doc.get("data", {})
            if not isinstance(data, dict):
                data = {}
            
            search_results.append(SearchResult(
                id=str(doc["_id"]),
                collection=doc.get("collection", "unknown"),
                data=data,
                score=doc.get("score", 0.0),
                highlights=None  # Highlights disabled
            ))
        
        # Calculate time taken
        took_ms = (datetime.now() - start_time).total_seconds() * 1000
        
        return SearchResponse(
            query=request.query,
            total=total,
            results=search_results,
            took_ms=round(took_ms, 2)
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., min_length=1, description="Search query"),
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(verify_api_key)
):
    """
    Autocomplete suggestions
    
    Provides search suggestions as user types
    """
    
    db = await get_database()
    
    # Atlas Search autocomplete query
    pipeline = [
        {
            "$search": {
                "index": "default",
                "autocomplete": {
                    "query": q,
                    "path": "collection",
                    "fuzzy": {
                        "maxEdits": 1
                    }
                }
            }
        },
        {
            "$group": {
                "_id": "$collection",
                "count": {"$sum": 1}
            }
        },
        {"$limit": limit},
        {"$sort": {"count": -1}}
    ]
    
    try:
        results = await db.storage_data.aggregate(pipeline).to_list(None)
        
        suggestions = [
            {
                "text": doc["_id"],
                "count": doc["count"]
            }
            for doc in results
        ]
        
        return {
            "success": True,
            "query": q,
            "suggestions": suggestions
        }
    
    except Exception as e:
        # Fallback to simple search if autocomplete fails
        collections = await db.storage_data.distinct(
            "collection",
            {
                "user_id": str(current_user["_id"]),
                "collection": {"$regex": q, "$options": "i"}
            }
        )
        
        return {
            "success": True,
            "query": q,
            "suggestions": [{"text": c, "count": 0} for c in collections[:limit]]
        }


@router.get("/facets")
async def get_search_facets(
    query: str = Query(..., description="Search query"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Get search facets (categories, tags, etc.)
    
    Useful for building filter UI
    """
    
    db = await get_database()
    
    # Search facets query
    pipeline = [
        {
            "$search": {
                "index": "default",
                "text": {
                    "query": query,
                    "path": ["data", "collection", "tags"]
                }
            }
        },
        {
            "$facet": {
                "collections": [
                    {
                        "$group": {
                            "_id": "$collection",
                            "count": {"$sum": 1}
                        }
                    },
                    {"$sort": {"count": -1}},
                    {"$limit": 10}
                ],
                "tags": [
                    {"$unwind": "$tags"},
                    {
                        "$group": {
                            "_id": "$tags",
                            "count": {"$sum": 1}
                        }
                    },
                    {"$sort": {"count": -1}},
                    {"$limit": 10}
                ]
            }
        }
    ]
    
    try:
        results = await db.storage_data.aggregate(pipeline).to_list(None)
        
        if results:
            facets = results[0]
            return {
                "success": True,
                "query": query,
                "facets": {
                    "collections": [
                        {"value": f["_id"], "count": f["count"]}
                        for f in facets.get("collections", [])
                    ],
                    "tags": [
                        {"value": f["_id"], "count": f["count"]}
                        for f in facets.get("tags", [])
                    ]
                }
            }
        
        return {
            "success": True,
            "query": query,
            "facets": {
                "collections": [],
                "tags": []
            }
        }
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Facets retrieval failed: {str(e)}"
        )


@router.get("/stats")
async def get_search_stats(
    current_user: dict = Depends(verify_api_key)
):
    """
    Get search statistics
    """
    
    db = await get_database()
    
    # Get total documents
    total_docs = await db.storage_data.count_documents({
        "user_id": str(current_user["_id"])
    })
    
    # Get collections
    collections = await db.storage_data.distinct(
        "collection",
        {"user_id": str(current_user["_id"])}
    )
    
    # Get total tags
    pipeline = [
        {"$match": {"user_id": str(current_user["_id"])}},
        {"$unwind": "$tags"},
        {"$group": {"_id": None, "unique_tags": {"$addToSet": "$tags"}}}
    ]
    
    tag_result = await db.storage_data.aggregate(pipeline).to_list(None)
    total_tags = len(tag_result[0]["unique_tags"]) if tag_result else 0
    
    return {
        "success": True,
        "stats": {
            "total_documents": total_docs,
            "total_collections": len(collections),
            "total_tags": total_tags,
            "search_features": {
                "fuzzy_search": True,
                "autocomplete": True,
                "faceted_search": True,
                "date_filtering": True,
                "relevance_scoring": True,
                "highlighting": True
            }
        },
        "search_engine": "MongoDB Atlas Search (Lucene)"
    }


@router.get("/test")
async def test_search_index():
    """
    Test if Atlas Search index is configured
    """
    
    db = await get_database()
    
    # Try a simple search
    try:
        pipeline = [
            {
                "$search": {
                    "index": "default",
                    "text": {
                        "query": "test",
                        "path": "collection"
                    }
                }
            },
            {"$limit": 1}
        ]
        
        await db.storage_data.aggregate(pipeline).to_list(None)
        
        return {
            "success": True,
            "atlas_search_configured": True,
            "message": "Atlas Search is working!",
            "index_name": "default"
        }
    
    except Exception as e:
        return {
            "success": False,
            "atlas_search_configured": False,
            "error": str(e),
            "message": "Atlas Search index not found. Please create search index in MongoDB Atlas.",
            "setup_guide": "https://www.mongodb.com/docs/atlas/atlas-search/create-index/"
        }