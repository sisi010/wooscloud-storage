"""
Smart Storage Router
Routes data to MongoDB or R2 based on size
Compatible with storage_router.py and batch_router.py
"""

import json
from typing import Optional, Dict, Any
from datetime import datetime
from bson import ObjectId
import io

from app.services.r2_storage import R2Storage

# Size threshold: 100KB
SIZE_THRESHOLD = 100 * 1024  # 100KB

class SmartStorageRouter:
    """Routes data storage to MongoDB or R2 based on size"""
    
    def __init__(self, mongodb_collection, r2_storage: Optional[R2Storage] = None):
        self.mongodb_collection = mongodb_collection
        self.r2_storage = r2_storage
    
    async def save(self, user_id: str, collection: str, data: dict) -> dict:
        """
        Save data to MongoDB or R2 based on size
        
        Args:
            user_id: User ID
            collection: Collection name
            data: Data to save
        
        Returns:
            dict with id, _id, collection, size, storage_type, created_at, updated_at
        """
        # Calculate size
        data_str = json.dumps(data, ensure_ascii=False)
        data_size = len(data_str.encode('utf-8'))
        
        # Determine storage location
        storage_type = "r2" if (data_size >= SIZE_THRESHOLD and self.r2_storage) else "mongodb"
        
        data_id = str(ObjectId())
        
        # Create document
        document = {
            "_id": data_id,
            "collection": collection,
            "user_id": user_id,
            "size": data_size,
            "storage_type": storage_type,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        if storage_type == "r2":
            # Store in R2
            r2_key = f"{collection}/{user_id}/{data_id}.json"
            
            try:
                self.r2_storage.upload_file(
                    file_obj=io.BytesIO(data_str.encode('utf-8')),
                    key=r2_key,
                    content_type="application/json"
                )
                
                document["r2_key"] = r2_key
                document["r2_url"] = self.r2_storage.get_url(r2_key)
                
            except Exception as e:
                raise Exception(f"Failed to upload to R2: {str(e)}")
        else:
            # Store in MongoDB
            document["data"] = data
        
        # Save metadata to MongoDB
        await self.mongodb_collection.insert_one(document)
        
        return {
            "id": data_id,
            "_id": data_id,  # For compatibility
            "collection": collection,
            "size": data_size,
            "storage_type": storage_type,
            "created_at": document["created_at"].isoformat(), 
            "updated_at": document["updated_at"].isoformat() 
        }
    
    async def get(self, data_id: str) -> Optional[dict]:
        """
        Get data by ID (legacy method for storage_router.py)
        Does not check user_id
        
        Returns:
            Data dict or None
        """
        # Get metadata
        document = await self.mongodb_collection.find_one({"_id": data_id})
        
        if not document:
            return None
        
        storage_type = document["storage_type"]
        
        if storage_type == "r2":
            # Retrieve from R2
            r2_key = document["r2_key"]
            
            try:
                content = self.r2_storage.download_file(r2_key)
                data = json.loads(content.decode('utf-8'))
                return data
            except Exception as e:
                print(f"Failed to retrieve from R2: {e}")
                return None
        else:
            # Get from MongoDB
            return document.get("data")
    
    async def retrieve(self, user_id: str, data_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data from MongoDB or R2 with user_id check
        
        Returns:
            dict with full metadata and data, or None if not found
        """
        # Get metadata
        document = await self.mongodb_collection.find_one({
            "_id": data_id,
            "user_id": user_id
        })
        
        if not document:
            return None
        
        storage_type = document["storage_type"]
        
        if storage_type == "r2":
            # Retrieve from R2
            r2_key = document["r2_key"]
            
            try:
                content = self.r2_storage.download_file(r2_key)
                data = json.loads(content.decode('utf-8'))
            except Exception as e:
                raise Exception(f"Failed to retrieve from R2: {str(e)}")
        else:
            # Get from MongoDB
            data = document.get("data", {})
        
        return {
            "id": document["_id"],
            "collection": document["collection"],
            "data": data,
            "size": document["size"],
            "storage_type": storage_type,
            "created_at": document["created_at"].isoformat(),
            "updated_at": document["updated_at"].isoformat()
        }
    
    async def update(self, data_id: str, new_data: dict) -> bool:
        """
        Update data by ID (legacy method for storage_router.py)
        Does not check user_id
        
        Returns:
            True if successful, False otherwise
        """
        # Get existing document
        document = await self.mongodb_collection.find_one({"_id": data_id})
        
        if not document:
            return False
        
        # Calculate new size
        data_str = json.dumps(new_data, ensure_ascii=False)
        new_size = len(data_str.encode('utf-8'))
        
        storage_type = document["storage_type"]
        
        try:
            if storage_type == "r2":
                # Update in R2
                r2_key = document["r2_key"]
                
                self.r2_storage.upload_file(
                    file_obj=io.BytesIO(data_str.encode('utf-8')),
                    key=r2_key,
                    content_type="application/json"
                )
            else:
                # Update in MongoDB
                await self.mongodb_collection.update_one(
                    {"_id": data_id},
                    {"$set": {"data": new_data}}
                )
            
            # Update metadata
            await self.mongodb_collection.update_one(
                {"_id": data_id},
                {
                    "$set": {
                        "size": new_size,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return True
            
        except Exception as e:
            print(f"Failed to update: {e}")
            return False
    
    async def update_with_user(self, user_id: str, data_id: str, new_data: dict) -> Optional[Dict[str, Any]]:
        """
        Update data with user_id check (for batch operations)
        
        Returns:
            dict with update info, or None if not found
        """
        # Get existing document
        document = await self.mongodb_collection.find_one({
            "_id": data_id,
            "user_id": user_id
        })
        
        if not document:
            return None
        
        # Calculate new size
        data_str = json.dumps(new_data, ensure_ascii=False)
        new_size = len(data_str.encode('utf-8'))
        
        storage_type = document["storage_type"]
        
        try:
            if storage_type == "r2":
                # Update in R2
                r2_key = document["r2_key"]
                
                self.r2_storage.upload_file(
                    file_obj=io.BytesIO(data_str.encode('utf-8')),
                    key=r2_key,
                    content_type="application/json"
                )
            else:
                # Update in MongoDB
                await self.mongodb_collection.update_one(
                    {"_id": data_id, "user_id": user_id},
                    {"$set": {"data": new_data}}
                )
            
            # Update metadata
            await self.mongodb_collection.update_one(
                {"_id": data_id, "user_id": user_id},
                {
                    "$set": {
                        "size": new_size,
                        "updated_at": datetime.utcnow()
                    }
                }
            )
            
            return {
                "id": data_id,
                "size": new_size,
                "storage_type": storage_type
            }
            
        except Exception as e:
            raise Exception(f"Failed to update: {str(e)}")
    
    async def delete(self, data_id: str) -> bool:
        """
        Delete data by ID (legacy method for storage_router.py)
        Does not check user_id
        
        Returns:
            True if successful, False otherwise
        """
        # Get document
        document = await self.mongodb_collection.find_one({"_id": data_id})
        
        if not document:
            return False
        
        storage_type = document["storage_type"]
        
        # Delete from R2 if stored there
        if storage_type == "r2":
            try:
                self.r2_storage.delete_file(document["r2_key"])
            except Exception as e:
                print(f"Warning: Failed to delete from R2: {e}")
        
        # Delete metadata from MongoDB
        result = await self.mongodb_collection.delete_one({"_id": data_id})
        
        return result.deleted_count > 0
    
    async def delete_with_user(self, user_id: str, data_id: str) -> Dict[str, Any]:
        """
        Delete data with user_id check (for batch operations)
        
        Returns:
            dict with success status and freed size
        """
        # Get document
        document = await self.mongodb_collection.find_one({
            "_id": data_id,
            "user_id": user_id
        })
        
        if not document:
            return {"success": False, "size": 0}
        
        storage_type = document["storage_type"]
        data_size = document["size"]
        
        # Delete from R2 if stored there
        if storage_type == "r2":
            try:
                self.r2_storage.delete_file(document["r2_key"])
            except Exception as e:
                print(f"Warning: Failed to delete from R2: {e}")
        
        # Delete metadata from MongoDB
        result = await self.mongodb_collection.delete_one({
            "_id": data_id,
            "user_id": user_id
        })
        
        return {
            "success": result.deleted_count > 0,
            "size": data_size
        }