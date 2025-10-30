"""
High-level storage interface for WoosCloud
"""

from typing import Dict, Any, List, Optional
from .client import WoosCloudClient
from .models import StorageData, StorageStats, Collection
from .exceptions import ValidationError

class WoosStorage:
    """
    High-level interface for WoosCloud Storage
    
    Example:
        >>> storage = WoosStorage(api_key="wai_abc123...")
        >>> storage.save("users", {"name": "John", "age": 30})
        >>> users = storage.find("users")
        >>> stats = storage.stats()
    """
    
    def __init__(self, api_key: str, base_url: str = "http://127.0.0.1:8000"):
        """
        Initialize WoosStorage
        
        Args:
            api_key: Your WoosCloud API key
            base_url: API base URL (default: localhost for development)
        """
        if not api_key or not api_key.startswith("wai_"):
            raise ValidationError("Invalid API key. Must start with 'wai_'")
        
        self.client = WoosCloudClient(api_key, base_url)
    
    def save(self, collection: str, data: Dict[str, Any]) -> str:
        """
        Save data to a collection
        
        Args:
            collection: Collection name
            data: Data to save (must be JSON serializable)
        
        Returns:
            Data ID
        
        Example:
            >>> data_id = storage.save("products", {
            ...     "name": "Laptop",
            ...     "price": 1500
            ... })
        """
        if not collection:
            raise ValidationError("Collection name is required")
        if not isinstance(data, dict):
            raise ValidationError("Data must be a dictionary")
        
        response = self.client.post("/api/storage/create", json={
            "collection": collection,
            "data": data
        })
        
        return response["id"]
    
    def find(
        self,
        collection: str,
        limit: int = 100,
        skip: int = 0
    ) -> List[StorageData]:
        """
        Find data in a collection
        
        Args:
            collection: Collection name
            limit: Maximum number of results (1-1000)
            skip: Number of results to skip
        
        Returns:
            List of StorageData objects
        
        Example:
            >>> products = storage.find("products", limit=10)
            >>> for product in products:
            ...     print(product.data)
        """
        if not collection:
            raise ValidationError("Collection name is required")
        
        response = self.client.get("/api/storage/list", params={
            "collection": collection,
            "limit": limit,
            "skip": skip
        })
        
        return [StorageData(**item) for item in response["data"]]
    
    def find_one(self, data_id: str) -> StorageData:
        """
        Find data by ID
        
        Args:
            data_id: Data ID
        
        Returns:
            StorageData object
        
        Example:
            >>> data = storage.find_one("673f1234...")
            >>> print(data.data)
        """
        if not data_id:
            raise ValidationError("Data ID is required")
        
        response = self.client.get(f"/api/storage/read/{data_id}")
        
        return StorageData(
            id=response["id"],
            collection=response["collection"],
            data=response["data"],
            size=0,  # Not returned by read endpoint
            created_at=response["created_at"],
            updated_at=response["updated_at"]
        )
    
    def update(self, data_id: str, data: Dict[str, Any]) -> bool:
        """
        Update data by ID
        
        Args:
            data_id: Data ID
            data: New data
        
        Returns:
            True if successful
        
        Example:
            >>> storage.update("673f1234...", {"name": "Updated Name"})
        """
        if not data_id:
            raise ValidationError("Data ID is required")
        if not isinstance(data, dict):
            raise ValidationError("Data must be a dictionary")
        
        self.client.put(f"/api/storage/update/{data_id}", json={"data": data})
        return True
    
    def delete(self, data_id: str) -> bool:
        """
        Delete data by ID
        
        Args:
            data_id: Data ID
        
        Returns:
            True if successful
        
        Example:
            >>> storage.delete("673f1234...")
        """
        if not data_id:
            raise ValidationError("Data ID is required")
        
        self.client.delete(f"/api/storage/delete/{data_id}")
        return True
    
    def stats(self) -> StorageStats:
        """
        Get storage usage statistics
        
        Returns:
            StorageStats object
        
        Example:
            >>> stats = storage.stats()
            >>> print(f"Used: {stats.storage_used_mb} MB")
            >>> print(f"API calls: {stats.api_calls_count}")
        """
        response = self.client.get("/api/storage/stats")
        return StorageStats(response["stats"])
    
    def collections(self) -> List[Collection]:
        """
        List all collections
        
        Returns:
            List of Collection objects
        
        Example:
            >>> collections = storage.collections()
            >>> for col in collections:
            ...     print(f"{col.name}: {col.count} items")
        """
        response = self.client.get("/api/storage/collections")
        return [Collection(**col) for col in response["collections"]]
    
    def count(self, collection: str) -> int:
        """
        Count items in a collection
        
        Args:
            collection: Collection name
        
        Returns:
            Number of items
        
        Example:
            >>> count = storage.count("products")
            >>> print(f"Total products: {count}")
        """
        if not collection:
            raise ValidationError("Collection name is required")
        
        response = self.client.get("/api/storage/list", params={
            "collection": collection,
            "limit": 1
        })
        
        return response["total"]