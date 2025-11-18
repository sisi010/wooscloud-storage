"""
Data models for WoosCloud Storage
"""

from typing import Optional, Dict, Any
from datetime import datetime

class StorageData:
    """Storage data model with R2 support"""
    
    def __init__(
        self,
        id: str,
        collection: str,
        data: Dict[str, Any],
        size: int = 0,
        storage_type: str = "mongodb",  # NEW!
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        **kwargs  # Accept any additional fields
    ):
        self.id = id
        self.collection = collection
        self.data = data
        self.size = size
        self.storage_type = storage_type  # NEW!
        self.created_at = created_at
        self.updated_at = updated_at
        
        # Store any additional fields
        for key, value in kwargs.items():
            setattr(self, key, value)
    
    def get(self, key: str, default=None):
        """Dictionary-like get method"""
        return getattr(self, key, default)
    
    def __getitem__(self, key: str):
        """Dictionary-like access"""
        return getattr(self, key)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        result = {
            "id": self.id,
            "collection": self.collection,
            "data": self.data,
            "size": self.size,
            "storage_type": self.storage_type,
        }
        
        if self.created_at:
            result["created_at"] = self.created_at
        if self.updated_at:
            result["updated_at"] = self.updated_at
            
        return result
    
    def __repr__(self):
        return f"StorageData(id={self.id}, collection={self.collection}, storage_type={self.storage_type})"


class StorageStats:
    """Storage statistics model"""
    
    def __init__(
        self,
        plan: str = None,
        storage_limit: int = None,
        storage_used: int = None,
        api_calls_count: int = None,
        api_calls_limit: int = None,
        storage_used_mb: float = None,
        storage_limit_mb: float = None,
        api_calls_used: int = None,
        **kwargs
    ):
        self.plan = plan
    
        # Support both old and new naming conventions
        self.storage_used_mb = storage_used_mb or (storage_used / (1024 * 1024) if storage_used else 0)
        self.storage_limit_mb = storage_limit_mb or (storage_limit / (1024 * 1024) if storage_limit else 0)
    
        self.api_calls_used = api_calls_used or api_calls_count or 0
        self.api_calls_limit = api_calls_limit or -1
    
        # Keep old attributes for backward compatibility
        self.storage_used = storage_used
        self.storage_limit = storage_limit
        self.api_calls_count = api_calls_count
        
        # Handle both old format (nested dict) and new format (flat)
        if isinstance(plan, dict):
            # Old format: StorageStats(stats_data)
            stats_data = plan
            
            # Storage info
            storage = stats_data.get('storage', {})
            self.used = storage.get('used', 0)
            self.limit = storage.get('limit', 0)
            self.percent = storage.get('percent', 0)
            self.used_mb = storage.get('used_mb', 0)
            self.limit_mb = storage.get('limit_mb', 0)
            
            # API calls info
            api_calls = stats_data.get('api_calls', {})
            self.api_calls_count = api_calls.get('count', 0)
            self.api_calls_limit = api_calls.get('limit', 0)
            self.api_calls_remaining = api_calls.get('remaining', 0)
            
            # Plan
            self.plan = stats_data.get('plan', 'free')
            
            # R2 info
            self.r2_enabled = stats_data.get('r2_enabled', False)
            
            # Storage distribution
            distribution = stats_data.get('storage_distribution', {})
            self.mongodb_items = distribution.get('mongodb', 0)
            self.r2_items = distribution.get('r2', 0)
            self.total_items = distribution.get('total', 0)
            
            # Computed properties for new format compatibility
            self.storage_limit = self.limit
            self.storage_used = self.used
            self.storage_limit_mb = self.limit_mb
            self.storage_used_mb = self.used_mb
            
        else:
            # New format: StorageStats(plan, storage_limit, storage_used, ...)
            self.plan = plan
            self.storage_limit = storage_limit or 0
            self.storage_used = storage_used or 0
            self.api_calls_count = api_calls_count or 0
            self.api_calls_limit = api_calls_limit or 0
            
            # Computed properties
            self.storage_limit_mb = self.storage_limit / 1024 / 1024
            self.storage_used_mb = self.storage_used / 1024 / 1024
            
            # Old format compatibility
            self.used = self.storage_used
            self.limit = self.storage_limit
            self.used_mb = self.storage_used_mb
            self.limit_mb = self.storage_limit_mb
            self.percent = (self.storage_used / self.storage_limit * 100) if self.storage_limit > 0 else 0
            
            # Defaults
            self.r2_enabled = kwargs.get('r2_enabled', False)
            self.mongodb_items = kwargs.get('mongodb_items', 0)
            self.r2_items = kwargs.get('r2_items', 0)
            self.total_items = kwargs.get('total_items', 0)
            self.api_calls_remaining = kwargs.get('api_calls_remaining', 0)
        
        # Store any additional fields
        for key, value in kwargs.items():
            if not hasattr(self, key):
                setattr(self, key, value)
    
    def get(self, key: str, default=None):
        """Dictionary-like get method"""
        return getattr(self, key, default)
    
    def __getitem__(self, key: str):
        """Dictionary-like access"""
        return getattr(self, key)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "storage": {
                "used": self.used,
                "limit": self.limit,
                "percent": self.percent,
                "used_mb": self.used_mb,
                "limit_mb": self.limit_mb
            },
            "api_calls": {
                "count": self.api_calls_count,
                "limit": self.api_calls_limit,
                "remaining": self.api_calls_remaining
            },
            "plan": self.plan,
            "r2_enabled": self.r2_enabled,
            "storage_distribution": {
                "mongodb": self.mongodb_items,
                "r2": self.r2_items,
                "total": self.total_items
            }
        }
    
    def __repr__(self):
        return f"StorageStats(plan={self.plan}, used_mb={self.storage_used_mb:.2f}, limit_mb={self.storage_limit_mb:.0f})"


class Collection:
    """Collection statistics"""
    
    def __init__(self, collection_data: Dict[str, Any]):
        self.name = collection_data.get('name', '')
        self.count = collection_data.get('count', 0)
        self.size = collection_data.get('size', 0)
        self.size_kb = collection_data.get('size_kb', 0)
        
        # R2 info (NEW!)
        self.mongodb_count = collection_data.get('mongodb_count', 0)
        self.r2_count = collection_data.get('r2_count', 0)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "name": self.name,
            "count": self.count,
            "size": self.size,
            "size_kb": self.size_kb,
            "mongodb_count": self.mongodb_count,
            "r2_count": self.r2_count
        }
    
    def __repr__(self):
        return f"Collection(name={self.name}, count={self.count}, mongodb={self.mongodb_count}, r2={self.r2_count})"