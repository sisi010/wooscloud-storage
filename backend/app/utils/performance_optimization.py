"""
Performance Optimization Module
MongoDB indexing, caching, and query optimization
"""

from functools import lru_cache
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import asyncio


# ============================================================================
# 1. MongoDB Index Creation
# ============================================================================

async def create_performance_indexes(db):
    """
    Create optimized indexes for better query performance
    
    Run this once during deployment or migration
    """
    
    indexes_created = []
    
    try:
        # Storage data indexes
        storage_collection = db.storage_data
        
        # 1. User ID + Created Date (for list queries)
        await storage_collection.create_index([
            ("user_id", 1),
            ("created_at", -1)
        ], name="user_created_idx")
        indexes_created.append("user_created_idx")
        
        # 2. User ID + Collection (for filtering)
        await storage_collection.create_index([
            ("user_id", 1),
            ("collection", 1)
        ], name="user_collection_idx")
        indexes_created.append("user_collection_idx")
        
        # 3. User ID + Tags (for tag filtering)
        await storage_collection.create_index([
            ("user_id", 1),
            ("tags", 1)
        ], name="user_tags_idx")
        indexes_created.append("user_tags_idx")
        
        # 4. Collection only (for stats)
        await storage_collection.create_index([
            ("collection", 1)
        ], name="collection_idx")
        indexes_created.append("collection_idx")
        
        # Users collection indexes
        users_collection = db.users
        
        # 5. Email (for login)
        await users_collection.create_index([
            ("email", 1)
        ], unique=True, name="email_unique_idx")
        indexes_created.append("email_unique_idx")
        
        # 6. API Keys (for authentication)
        await users_collection.create_index([
            ("api_keys.key", 1)
        ], name="api_keys_idx")
        indexes_created.append("api_keys_idx")
        
        # API Keys collection indexes
        api_keys_collection = db.api_keys
        
        # 7. Key hash (for fast lookup)
        await api_keys_collection.create_index([
            ("key_hash", 1)
        ], unique=True, name="key_hash_idx")
        indexes_created.append("key_hash_idx")
        
        # 8. User ID + Status (for active keys)
        await api_keys_collection.create_index([
            ("user_id", 1),
            ("status", 1)
        ], name="user_status_idx")
        indexes_created.append("user_status_idx")
        
        print(f"✅ Created {len(indexes_created)} indexes: {', '.join(indexes_created)}")
        return {"success": True, "indexes": indexes_created}
    
    except Exception as e:
        print(f"❌ Index creation error: {e}")
        return {"success": False, "error": str(e), "indexes": indexes_created}


# ============================================================================
# 2. Redis-like In-Memory Cache
# ============================================================================

class SimpleCache:
    """
    Simple in-memory cache with TTL
    Thread-safe for asyncio
    """
    
    def __init__(self):
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        async with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if datetime.now() < entry["expires_at"]:
                    return entry["value"]
                else:
                    # Expired, remove
                    del self._cache[key]
            return None
    
    async def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """Set value in cache with TTL (default 5 minutes)"""
        async with self._lock:
            self._cache[key] = {
                "value": value,
                "expires_at": datetime.now() + timedelta(seconds=ttl_seconds)
            }
    
    async def delete(self, key: str):
        """Delete key from cache"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    async def clear(self):
        """Clear all cache"""
        async with self._lock:
            self._cache.clear()
    
    async def cleanup_expired(self):
        """Remove expired entries"""
        async with self._lock:
            now = datetime.now()
            expired_keys = [
                key for key, entry in self._cache.items()
                if now >= entry["expires_at"]
            ]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)


# Global cache instance
cache = SimpleCache()


# ============================================================================
# 3. Optimized Query Helpers
# ============================================================================

async def get_storage_stats_optimized(db, user_id: str):
    """
    Optimized storage stats with caching
    
    Uses aggregation pipeline with indexes
    """
    
    # Check cache first
    cache_key = f"stats:{user_id}"
    cached = await cache.get(cache_key)
    if cached:
        cached["from_cache"] = True
        return cached
    
    # Aggregation pipeline (uses indexes)
    pipeline = [
        {"$match": {"user_id": user_id}},
        {
            "$group": {
                "_id": None,
                "total_documents": {"$sum": 1},
                "collections": {"$addToSet": "$collection"},
                "total_size": {"$sum": {"$ifNull": ["$metadata.size", 0]}}
            }
        }
    ]
    
    result = await db.storage_data.aggregate(pipeline).to_list(1)
    
    if result:
        stats = {
            "total_documents": result[0]["total_documents"],
            "total_collections": len(result[0]["collections"]),
            "total_size_bytes": result[0]["total_size"],
            "from_cache": False
        }
    else:
        stats = {
            "total_documents": 0,
            "total_collections": 0,
            "total_size_bytes": 0,
            "from_cache": False
        }
    
    # Cache for 5 minutes
    await cache.set(cache_key, stats, ttl_seconds=300)
    
    return stats


async def get_storage_list_optimized(
    db,
    user_id: str,
    skip: int = 0,
    limit: int = 10,
    collection: Optional[str] = None
):
    """
    Optimized storage list with projection
    
    Only fetches needed fields, uses indexes
    """
    
    # Build query
    query = {"user_id": user_id}
    if collection:
        query["collection"] = collection
    
    # Projection (only get needed fields)
    projection = {
        "_id": 1,
        "collection": 1,
        "created_at": 1,
        "updated_at": 1,
        "tags": 1,
        "metadata": 1
        # Exclude large 'data' field unless needed
    }
    
    # Execute query with index hint
    cursor = db.storage_data.find(query, projection).sort(
        "created_at", -1
    ).skip(skip).limit(limit)
    
    documents = await cursor.to_list(length=limit)
    
    return documents


async def get_collection_counts_optimized(db, user_id: str):
    """
    Get document count per collection (optimized)
    """
    
    cache_key = f"collections:{user_id}"
    cached = await cache.get(cache_key)
    if cached:
        return cached
    
    pipeline = [
        {"$match": {"user_id": user_id}},
        {
            "$group": {
                "_id": "$collection",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"count": -1}}
    ]
    
    results = await db.storage_data.aggregate(pipeline).to_list(None)
    
    collections = {
        item["_id"]: item["count"]
        for item in results
    }
    
    # Cache for 5 minutes
    await cache.set(cache_key, collections, ttl_seconds=300)
    
    return collections


# ============================================================================
# 4. Batch Operations Optimization
# ============================================================================

async def batch_insert_optimized(db, documents: list):
    """
    Optimized batch insert with ordered=False
    
    Continues on error, faster for large batches
    """
    
    if not documents:
        return {"inserted": 0, "errors": []}
    
    try:
        result = await db.storage_data.insert_many(
            documents,
            ordered=False  # Don't stop on first error
        )
        return {
            "inserted": len(result.inserted_ids),
            "errors": []
        }
    except Exception as e:
        # Partial success possible with ordered=False
        return {
            "inserted": 0,
            "errors": [str(e)]
        }


# ============================================================================
# 5. Connection Pool Optimization
# ============================================================================

def get_optimized_mongo_client(connection_string: str):
    """
    Create MongoDB client with optimized connection pool
    """
    from motor.motor_asyncio import AsyncIOMotorClient
    
    client = AsyncIOMotorClient(
        connection_string,
        maxPoolSize=50,          # Increase pool size
        minPoolSize=10,          # Keep connections alive
        maxIdleTimeMS=45000,     # Keep idle connections
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=10000,
        socketTimeoutMS=45000,
        retryWrites=True,
        retryReads=True
    )
    
    return client


# ============================================================================
# 6. Query Explain Helper (for debugging)
# ============================================================================

async def explain_query(db, collection_name: str, query: dict):
    """
    Explain query execution plan
    
    Useful for debugging slow queries
    """
    
    collection = db[collection_name]
    explain = await collection.find(query).explain()
    
    return {
        "execution_time_ms": explain.get("executionStats", {}).get("executionTimeMillis"),
        "docs_examined": explain.get("executionStats", {}).get("totalDocsExamined"),
        "docs_returned": explain.get("executionStats", {}).get("nReturned"),
        "index_used": explain.get("executionStats", {}).get("executionStages", {}).get("indexName"),
        "full_explain": explain
    }


# ============================================================================
# 7. Cache Warming (Startup)
# ============================================================================

async def warm_cache_on_startup(db):
    """
    Pre-load frequently accessed data into cache
    
    Call this during application startup
    """
    
    print("🔥 Warming up cache...")
    
    # Get top 10 active users
    pipeline = [
        {
            "$group": {
                "_id": "$user_id",
                "count": {"$sum": 1}
            }
        },
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    
    top_users = await db.storage_data.aggregate(pipeline).to_list(10)
    
    # Pre-cache their stats
    warmed = 0
    for user in top_users:
        user_id = user["_id"]
        await get_storage_stats_optimized(db, user_id)
        await get_collection_counts_optimized(db, user_id)
        warmed += 1
    
    print(f"✅ Warmed cache for {warmed} users")
    return warmed


# ============================================================================
# 8. Background Cache Cleanup Task
# ============================================================================

async def cache_cleanup_task():
    """
    Background task to clean expired cache entries
    
    Run this as a background task in main.py
    """
    
    while True:
        await asyncio.sleep(300)  # Every 5 minutes
        removed = await cache.cleanup_expired()
        if removed > 0:
            print(f"🧹 Cleaned {removed} expired cache entries")