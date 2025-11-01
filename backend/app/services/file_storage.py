"""
File storage service
Handles file upload/download with R2 integration
"""

import io
import mimetypes
from typing import Optional, Dict, Any, BinaryIO
from datetime import datetime
from bson import ObjectId

from app.services.r2_storage import R2Storage
from app.database import get_database
from app.config import settings

# File size threshold: 5MB
FILE_SIZE_THRESHOLD = 5 * 1024 * 1024  # 5MB

# Maximum file size: 100MB for free tier
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB

class FileStorageService:
    """Service for handling file storage operations"""
    
    def __init__(self, r2_storage: Optional[R2Storage] = None):
        self.r2_storage = r2_storage
    
    async def upload_file(
        self,
        file_content: bytes,
        filename: str,
        content_type: str,
        collection: str,
        user_id: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload file to MongoDB or R2 based on size
        
        Args:
            file_content: File binary content
            filename: Original filename
            content_type: MIME type
            collection: Collection name
            user_id: User ID
            metadata: Additional metadata
        
        Returns:
            Dict with file info and storage location
        """
        file_size = len(file_content)
        
        # Check file size limit
        if file_size > MAX_FILE_SIZE:
            raise ValueError(f"File size exceeds limit: {MAX_FILE_SIZE} bytes")
        
        # Determine storage location
        storage_type = "r2" if (file_size >= FILE_SIZE_THRESHOLD and self.r2_storage) else "mongodb"
        
        db = await get_database()
        file_id = str(ObjectId())
        
        # Prepare file document
        file_doc = {
            "_id": file_id,
            "filename": filename,
            "content_type": content_type,
            "size": file_size,
            "storage_type": storage_type,
            "collection": collection,
            "user_id": user_id,
            "metadata": metadata or {},
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        if storage_type == "r2":
            # Upload to R2
            r2_key = f"{collection}/{file_id}/{filename}"
            
            try:
                self.r2_storage.upload_file(
                    file_obj=io.BytesIO(file_content),
                    key=r2_key,
                    content_type=content_type
                )
                
                file_doc["r2_key"] = r2_key
                file_doc["r2_url"] = self.r2_storage.get_url(r2_key)
                
            except Exception as e:
                raise Exception(f"Failed to upload to R2: {str(e)}")
        else:
            # Store in MongoDB
            file_doc["content"] = file_content
        
        # Save metadata to MongoDB
        await db.files.insert_one(file_doc)
        
        return {
            "id": file_id,
            "filename": filename,
            "content_type": content_type,
            "size": file_size,
            "storage_type": storage_type,
            "url": file_doc.get("r2_url"),
            "metadata": metadata,
            "created_at": file_doc["created_at"].isoformat()
        }
    
    async def download_file(self, file_id: str, user_id: str) -> Dict[str, Any]:
        """
        Download file from MongoDB or R2
        
        Returns:
            Dict with file content and metadata
        """
        db = await get_database()
        
        # Get file metadata
        file_doc = await db.files.find_one({"_id": file_id, "user_id": user_id})
        
        if not file_doc:
            raise ValueError("File not found")
        
        storage_type = file_doc["storage_type"]
        
        if storage_type == "r2":
            # Download from R2
            r2_key = file_doc["r2_key"]
            
            try:
                file_content = self.r2_storage.download_file(r2_key)
            except Exception as e:
                raise Exception(f"Failed to download from R2: {str(e)}")
        else:
            # Get from MongoDB
            file_content = file_doc["content"]
        
        return {
            "content": file_content,
            "filename": file_doc["filename"],
            "content_type": file_doc["content_type"],
            "size": file_doc["size"]
        }
    
    async def get_file_info(self, file_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """Get file metadata without downloading content"""
        db = await get_database()
        
        file_doc = await db.files.find_one(
            {"_id": file_id, "user_id": user_id},
            {"content": 0}  # Exclude content field
        )
        
        if not file_doc:
            return None
        
        return {
            "id": file_doc["_id"],
            "filename": file_doc["filename"],
            "content_type": file_doc["content_type"],
            "size": file_doc["size"],
            "storage_type": file_doc["storage_type"],
            "collection": file_doc["collection"],
            "metadata": file_doc.get("metadata", {}),
            "url": file_doc.get("r2_url"),
            "created_at": file_doc["created_at"].isoformat(),
            "updated_at": file_doc["updated_at"].isoformat()
        }
    
    async def delete_file(self, file_id: str, user_id: str) -> bool:
        """Delete file from storage"""
        db = await get_database()
        
        # Get file info
        file_doc = await db.files.find_one({"_id": file_id, "user_id": user_id})
        
        if not file_doc:
            return False
        
        # Delete from R2 if stored there
        if file_doc["storage_type"] == "r2":
            try:
                self.r2_storage.delete_file(file_doc["r2_key"])
            except Exception as e:
                print(f"Warning: Failed to delete from R2: {e}")
        
        # Delete metadata from MongoDB
        result = await db.files.delete_one({"_id": file_id, "user_id": user_id})
        
        return result.deleted_count > 0