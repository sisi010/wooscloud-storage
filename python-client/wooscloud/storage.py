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
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        skip: int = 0
    ) -> Dict[str, Any]:
        """
        Full-text search in a collection
        
        Args:
            collection: Collection name
            query: Search query text
            fields: List of fields to search (optional, searches all if not specified)
            filters: Additional filters to apply (optional)
            limit: Maximum results
            skip: Number of results to skip (pagination)
        
        Returns:
            Dict with 'total' and 'items' keys
            - total: Total number of matching documents
            - items: List of StorageData objects
        
        Example:
            >>> # Search all fields
            >>> results = storage.search("products", "laptop")
            >>> print(f"Found {results['total']} items")
            >>> for item in results["items"]:
            ...     print(item.data["name"])
            
            >>> # Search specific fields with filters
            >>> results = storage.search(
            ...     collection="products",
            ...     query="gaming",
            ...     fields=["name", "description"],
            ...     filters={"category": "Electronics"}
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
        
        if filters:
            for key, value in filters.items():
                params[f"filter_{key}"] = value
        
        response = self.client.get("/api/search", params=params)
        result = response
        
        # Convert results to StorageData objects
        items_data = result.get("results", result.get("items", []))
        items = [StorageData(**item) for item in items_data]
        
        return {
            "total": result.get("total", len(items)),
            "items": items
        }
    
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
    
    def export(
        self,
        collection: str,
        format: str = "json",
        fields: Optional[List[str]] = None,
        output_file: Optional[str] = None
    ) -> Optional[bytes]:
        """
        Export data from a collection
    
        Args:
           collection: Collection name
            format: Export format (json, csv, xlsx)
            fields: Optional list of fields to include
            output_file: Optional output file path
        
        Returns:
            File content as bytes if no output_file, None if saved
            
        Example:
            >>> # Export to JSON
            >>> storage.export("products", format="json", output_file="products.json")
        
            >>> # Export to CSV with specific fields
            >>> storage.export("products", format="csv", 
            ...                fields=["name", "price"], output_file="products.csv")
        
            >>> # Export to Excel
            >>> storage.export("products", format="xlsx", output_file="products.xlsx")
        """
        if not collection:
            raise ValidationError("Collection name is required")
    
        params = {
            "collection": collection,
            "format": format
        }
    
        if fields:
            params["fields"] = ",".join(fields)
    
        # Get raw response
        response = self.client.get_raw("/api/export", params=params)
    
        if output_file:
            # Save to file
            with open(output_file, "wb") as f:
                f.write(response.content)
            return None
        else:
            return response.content

    def export_preview(self, collection: str) -> Dict[str, Any]:
        """
        Preview export statistics
    
        Args:
            collection: Collection name
    
        Returns:
            Export preview information with 'record_count' and 'estimated_size_bytes'
    
        Example:
            >>> preview = storage.export_preview("products")
            >>> print(f"Records: {preview['record_count']}")
            >>> print(f"Size: {preview['estimated_size_bytes']} bytes")
        """
        if not collection:
            raise ValidationError("Collection name is required")

        result = self.client.get("/api/export/preview", params={"collection": collection})
    
        # Fix: Ensure estimated_size_bytes exists
        if "estimated_size_bytes" not in result:
            result["estimated_size_bytes"] = result.get("estimated_size", 0)
    
        return result