"""
Smart Storage Router
Automatically routes data to optimal storage (MongoDB or R2)
Small data (< 100KB) -> MongoDB
Large data (>= 100KB) -> R2
"""

import logging
import json
from typing import Dict, Any, Optional
from datetime import datetime
from bson import ObjectId
from .r2_storage import R2Storage

logger = logging.getLogger(__name__)

class SmartStorageRouter:
    """
    Automatically routes data to optimal storage based on size
    """
    
    # Threshold: 100KB
    SIZE_THRESHOLD = 100 * 1024
    
    def __init__(self, mongodb_collection, r2_storage: Optional[R2Storage] = None):
        """
        Initialize smart router
        
        Args:
            mongodb_collection: MongoDB collection
            r2_storage: R2 storage instance (optional)
        """
        self.mongodb = mongodb_collection
        self.r2 = r2_storage
        self.r2_enabled = r2_storage is not None
        
        logger.info(f"Smart router initialized (R2 enabled: {self.r2_enabled})")
    
    def _calculate_size(self, data: Dict[str, Any]) -> int:
        """Calculate data size in bytes"""
        json_str = json.dumps(data, ensure_ascii=False)
        return len(json_str.encode('utf-8'))
    
    def _should_use_r2(self, data_size: int) -> bool:
        """Determine if R2 should be used"""
        return self.r2_enabled and data_size >= self.SIZE_THRESHOLD
    
    async def save(
        self,
        user_id: str,
        collection: str,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Save data to optimal storage
        
        Args:
            user_id: User ID
            collection: Collection name
            data: Data to save
        
        Returns:
            Document with storage info
        """
        data_size = self._calculate_size(data)
        use_r2 = self._should_use_r2(data_size)
        
        now = datetime.utcnow()
        doc_id = ObjectId()
        
        if use_r2:
            # Large data -> R2
            r2_key = f"{user_id}/{collection}/{str(doc_id)}.json"
            
            try:
                # Store in R2
                self.r2.put_json(r2_key, data)
                
                # Store metadata in MongoDB
                document = {
                    "_id": doc_id,
                    "user_id": user_id,
                    "collection": collection,
                    "storage_type": "r2",
                    "r2_key": r2_key,
                    "size": data_size,
                    "data_preview": str(data)[:200],  # First 200 chars
                    "created_at": now,
                    "updated_at": now
                }
                
                await self.mongodb.insert_one(document)
                
                logger.info(f"Saved large data to R2: {r2_key} ({data_size} bytes)")
                return document
                
            except Exception as e:
                logger.error(f"Failed to save to R2: {e}")
                # Fallback to MongoDB
                logger.warning("Falling back to MongoDB")
                use_r2 = False
        
        if not use_r2:
            # Small data -> MongoDB
            document = {
                "_id": doc_id,
                "user_id": user_id,
                "collection": collection,
                "storage_type": "mongodb",
                "data": data,
                "size": data_size,
                "created_at": now,
                "updated_at": now
            }
            
            await self.mongodb.insert_one(document)
            
            logger.info(f"Saved data to MongoDB: {str(doc_id)} ({data_size} bytes)")
            return document
    
    async def get(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve data from storage
        
        Args:
            document_id: Document ID
        
        Returns:
            Data dictionary
        """
        # Get metadata from MongoDB
        doc = await self.mongodb.find_one({"_id": ObjectId(document_id)})
        
        if not doc:
            return None
        
        if doc.get("storage_type") == "r2":
            # Retrieve from R2
            try:
                data = self.r2.get_json(doc["r2_key"])
                logger.info(f"Retrieved from R2: {doc['r2_key']}")
                return data
            except Exception as e:
                logger.error(f"Failed to retrieve from R2: {e}")
                return None
        else:
            # Retrieve from MongoDB
            return doc.get("data")
    
    async def update(
        self,
        document_id: str,
        new_data: Dict[str, Any]
    ) -> bool:
        """
        Update data in storage
        
        Args:
            document_id: Document ID
            new_data: New data
        
        Returns:
            True if successful
        """
        doc = await self.mongodb.find_one({"_id": ObjectId(document_id)})
        
        if not doc:
            return False
        
        new_size = self._calculate_size(new_data)
        now = datetime.utcnow()
        
        if doc.get("storage_type") == "r2":
            # Update in R2
            try:
                self.r2.put_json(doc["r2_key"], new_data)
                
                # Update metadata
                await self.mongodb.update_one(
                    {"_id": ObjectId(document_id)},
                    {
                        "$set": {
                            "size": new_size,
                            "data_preview": str(new_data)[:200],
                            "updated_at": now
                        }
                    }
                )
                
                logger.info(f"Updated in R2: {doc['r2_key']}")
                return True
                
            except Exception as e:
                logger.error(f"Failed to update in R2: {e}")
                return False
        else:
            # Update in MongoDB
            await self.mongodb.update_one(
                {"_id": ObjectId(document_id)},
                {
                    "$set": {
                        "data": new_data,
                        "size": new_size,
                        "updated_at": now
                    }
                }
            )
            
            logger.info(f"Updated in MongoDB: {document_id}")
            return True
    
    async def delete(self, document_id: str) -> bool:
        """
        Delete data from storage
        
        Args:
            document_id: Document ID
        
        Returns:
            True if successful
        """
        doc = await self.mongodb.find_one({"_id": ObjectId(document_id)})
        
        if not doc:
            return False
        
        if doc.get("storage_type") == "r2":
            # Delete from R2
            try:
                self.r2.delete(doc["r2_key"])
                logger.info(f"Deleted from R2: {doc['r2_key']}")
            except Exception as e:
                logger.error(f"Failed to delete from R2: {e}")
        
        # Delete metadata from MongoDB
        await self.mongodb.delete_one({"_id": ObjectId(document_id)})
        
        logger.info(f"Deleted document: {document_id}")
        return True