"""
High-level storage interface for WoosCloud
"""

from typing import Dict, Any, List, Optional
from .client import WoosCloudClient
from .models import StorageData, StorageStats, Collection
from .exceptions import ValidationError
from .files import FileManager
from .webhooks import WebhookManager
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
        self.files = FileManager(self.client)
        self.webhooks = WebhookManager(self.client) 
        
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
        query: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        skip: int = 0
    ) -> List[StorageData]:
        """Find multiple data entries with R2 support"""
        params = {
            "collection": collection,
            "limit": limit,
            "skip": skip
        }
    
        if query:
            params["query"] = query
    
        response = self.client.get("/api/storage/list", params=params)
    
        items = []
        data_list = response.get("data", [])
    
        for item in data_list:
            try:
                # Handle both formats: direct item or wrapped in metadata
                if isinstance(item, dict):
                    # Check if it's wrapped format or direct format
                    if "data" in item and isinstance(item["data"], dict):
                        # Standard format
                        items.append(StorageData(
                            id=item.get("id", ""),
                            collection=item.get("collection", ""),
                            data=item.get("data", {}),
                            size=item.get("size", 0),
                            storage_type=item.get("storage_type", "mongodb"),
                            created_at=item.get("created_at"),
                            updated_at=item.get("updated_at")
                        ))
                    else:
                        # Item might be the data itself with _id
                        items.append(StorageData(
                            id=str(item.get("_id", item.get("id", ""))),
                            collection=collection,
                            data=item,
                            size=len(str(item)),
                            storage_type=item.get("storage_type", "mongodb"),
                            created_at=item.get("created_at"),
                            updated_at=item.get("updated_at")
                        ))
            except Exception as e:
                # Skip items that can't be parsed
                print(f"Warning: Could not parse item: {e}")
                continue
     
        return items
    
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
            storage_type=response.get("storage_type", "mongodb"),
            created_at=response["created_at"],
            updated_at=response["updated_at"]
        )
    
    def get(self, collection: str, item_id: str) -> Optional[StorageData]:
        """
        Get a single item by ID
        
        Args:
            collection: Collection name (not used, kept for API compatibility)
            item_id: Item ID
            
        Returns:
            StorageData object or None if not found
            
        Example:
            >>> item = storage.get("users", "673f1234...")
            >>> if item:
            ...     print(item.data)
        """
        try:
            return self.find_one(item_id)
        except Exception:
            return None
    
    def update(self, collection: str, item_id: str, data: Dict[str, Any]) -> bool:
        """
        Update an existing item
        
        Args:
            collection: Collection name (not used, kept for API compatibility)
            item_id: Item ID
            data: New data
            
        Returns:
            True if successful
            
        Example:
            >>> storage.update("users", "673f1234...", {"name": "Updated"})
        """
        if not item_id:
            raise ValidationError("Item ID is required")
        if not isinstance(data, dict):
            raise ValidationError("Data must be a dictionary")
        
        self.client.put(f"/api/storage/update/{item_id}", json={"data": data})
        return True
    
    def delete(self, collection: str, item_id: str) -> bool:
        """
        Delete an item
        
        Args:
            collection: Collection name (not used, kept for API compatibility)
            item_id: Item ID
            
        Returns:
            True if successful
            
        Example:
            >>> storage.delete("users", "673f1234...")
        """
        if not item_id:
            raise ValidationError("Item ID is required")
        
        self.client.delete(f"/api/storage/delete/{item_id}")
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
        return [Collection(col) for col in response["collections"]]
    
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
        
        return response.get("total", 0)
    
    def search(
        self,
        collection: str,
        query: str,
        fields: Optional[List[str]] = None,
        limit: int = 10,
        skip: int = 0
    ) -> Dict[str, Any]:
        """
        Full-text search in a collection
        
        Args:
            collection: Collection name
            query: Search query text
            fields: List of fields to search (optional, searches all if not specified)
            limit: Maximum results
            skip: Number of results to skip (pagination)
        
        Returns:
            Search results with metadata
        
        Example:
            >>> # Search all fields
            >>> results = storage.search("products", "laptop")
            >>> for item in results["results"]:
            ...     print(item["data"]["name"])
            
            >>> # Search specific fields
            >>> results = storage.search(
            ...     collection="products",
            ...     query="gaming",
            ...     fields=["name", "description"]
            ... )
        """
        if not collection:
            raise ValidationError("Collection name is required")
        if not query:
            raise ValidationError("Search query is required")
        
        params = {
            "collection": collection,
            "query": query,
            "limit": limit,
            "skip": skip
        }
        
        if fields:
            params["fields"] = ",".join(fields)
        
        return self.client.get("/api/search", params=params)
    
    def autocomplete(
        self,
        collection: str,
        field: str,
        prefix: str,
        limit: int = 10
    ) -> List[str]:
        """
        Get autocomplete suggestions
        
        Args:
            collection: Collection name
            field: Field name to search
            prefix: Text prefix to match
            limit: Maximum suggestions
        
        Returns:
            List of suggestion strings
        
        Example:
            >>> suggestions = storage.autocomplete(
            ...     collection="products",
            ...     field="name",
            ...     prefix="lap"
            ... )
            >>> print(suggestions)
            ["Laptop HP", "Laptop Dell", "Laptop Asus"]
        """
        if not collection:
            raise ValidationError("Collection name is required")
        if not field:
            raise ValidationError("Field name is required")
        if not prefix:
            raise ValidationError("Prefix is required")
        
        params = {
            "collection": collection,
            "field": field,
            "prefix": prefix,
            "limit": limit
        }
        
        response = self.client.get("/api/autocomplete", params=params)
        return response.get("suggestions", [])