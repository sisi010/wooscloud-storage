"""
Data models for WoosCloud Storage
"""

from typing import Dict, Any, List, Optional
from datetime import datetime

class StorageData:
    """Represents a stored data item"""
    
    def __init__(
        self,
        id: str,
        collection: str,
        data: Dict[str, Any],
        size: int,
        created_at: str,
        updated_at: str
    ):
        self.id = id
        self.collection = collection
        self.data = data
        self.size = size
        self.created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        self.updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
    
    def __repr__(self):
        return f"StorageData(id='{self.id}', collection='{self.collection}')"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "id": self.id,
            "collection": self.collection,
            "data": self.data,
            "size": self.size,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

class StorageStats:
    """Represents storage usage statistics"""
    
    def __init__(self, stats_data: Dict[str, Any]):
        storage = stats_data.get("storage", {})
        api_calls = stats_data.get("api_calls", {})
        
        self.storage_used = storage.get("used", 0)
        self.storage_limit = storage.get("limit", 0)
        self.storage_percent = storage.get("percent", 0)
        self.storage_used_mb = storage.get("used_mb", 0)
        self.storage_limit_mb = storage.get("limit_mb", 0)
        
        self.api_calls_count = api_calls.get("count", 0)
        self.api_calls_limit = api_calls.get("limit", 0)
        self.api_calls_remaining = api_calls.get("remaining", 0)
        
        self.plan = stats_data.get("plan", "free")
    
    def __repr__(self):
        return f"StorageStats(used={self.storage_used_mb}MB, calls={self.api_calls_count})"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "storage": {
                "used": self.storage_used,
                "limit": self.storage_limit,
                "percent": self.storage_percent,
                "used_mb": self.storage_used_mb,
                "limit_mb": self.storage_limit_mb
            },
            "api_calls": {
                "count": self.api_calls_count,
                "limit": self.api_calls_limit,
                "remaining": self.api_calls_remaining
            },
            "plan": self.plan
        }

class Collection:
    """Represents a data collection"""
    
    def __init__(self, name: str, count: int, size: int, size_kb: float):
        self.name = name
        self.count = count
        self.size = size
        self.size_kb = size_kb
    
    def __repr__(self):
        return f"Collection(name='{self.name}', count={self.count}, size={self.size_kb}KB)"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "count": self.count,
            "size": self.size,
            "size_kb": self.size_kb
        }