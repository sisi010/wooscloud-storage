"""
File operations for WoosCloud Storage
Handles file upload, download, and management
"""

from typing import Dict, Any, List, Optional, BinaryIO, Union
from pathlib import Path
import mimetypes

class FileManager:
    """Manages file operations"""
    
    def __init__(self, client):
        """
        Initialize FileManager
        
        Args:
            client: WoosCloudClient instance
        """
        self.client = client
    
    def upload(
        self,
        file_path: Union[str, Path, BinaryIO],
        collection: str,
        filename: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload a file
        
        Args:
            file_path: Path to file or file-like object
            collection: Collection name (e.g., "profile_images")
            filename: Custom filename (optional, auto-detected from path)
            description: File description
            tags: List of tags
            metadata: Custom metadata dictionary
            
        Returns:
            Upload response with file_id, storage_type, etc.
            
        Example:
            >>> # Upload from file path
            >>> result = storage.files.upload(
            ...     file_path="profile.jpg",
            ...     collection="profile_images",
            ...     description="User profile photo",
            ...     tags=["profile", "public"]
            ... )
            >>> print(result["id"])  # File ID
            
            >>> # Upload from file object
            >>> with open("document.pdf", "rb") as f:
            ...     result = storage.files.upload(
            ...         file_path=f,
            ...         collection="documents",
            ...         filename="document.pdf"
            ...     )
        """
        
        # Handle file-like object vs path
        if isinstance(file_path, (str, Path)):
            file_path = Path(file_path)
            
            if not file_path.exists():
                raise FileNotFoundError(f"File not found: {file_path}")
            
            if not filename:
                filename = file_path.name
            
            with open(file_path, "rb") as f:
                file_content = f.read()
        else:
            # File-like object
            if not filename:
                filename = getattr(file_path, "name", "unnamed_file")
            file_content = file_path.read()
        
        # Detect content type
        content_type, _ = mimetypes.guess_type(filename)
        if not content_type:
            content_type = "application/octet-stream"
        
        # Prepare form data
        files = {
            "file": (filename, file_content, content_type)
        }
        
        data = {
            "collection": collection
        }
        
        if description:
            data["description"] = description
        
        if tags:
            import json
            data["tags"] = json.dumps(tags)
        
        if metadata:
            import json
            data["custom_metadata"] = json.dumps(metadata)
        
        # Upload
        response = self.client.post(
            "/api/files/upload",
            files=files,
            data=data
        )
        
        return response
    
    def download(self, file_id: str, output_path: Optional[Union[str, Path]] = None) -> Union[bytes, None]:
        """
        Download a file
        
        Args:
            file_id: File ID
            output_path: Path to save file (optional)
            
        Returns:
            File content as bytes if no output_path, None if saved to file
            
        Example:
            >>> # Download to memory
            >>> content = storage.files.download("file_123")
            >>> with open("downloaded.jpg", "wb") as f:
            ...     f.write(content)
            
            >>> # Download directly to file
            >>> storage.files.download("file_123", "profile.jpg")
        """
        
        response = self.client.get_raw(f"/api/files/download/{file_id}")
        
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, "wb") as f:
                f.write(response.content)
            
            return None
        else:
            return response.content
    
    def get_info(self, file_id: str) -> Dict[str, Any]:
        """
        Get file information
        
        Args:
            file_id: File ID
            
        Returns:
            File metadata
            
        Example:
            >>> info = storage.files.get_info("file_123")
            >>> print(f"Size: {info['size']} bytes")
            >>> print(f"Type: {info['content_type']}")
        """
        
        return self.client.get(f"/api/files/file/{file_id}")
    
    def delete(self, file_id: str) -> Dict[str, Any]:
        """
        Delete a file
        
        Args:
            file_id: File ID
            
        Returns:
            Deletion result
            
        Example:
            >>> result = storage.files.delete("file_123")
            >>> print(f"Freed {result['freed_bytes']} bytes")
        """
        
        return self.client.delete(f"/api/files/file/{file_id}")
    
    def list(
        self,
        collection: Optional[str] = None,
        limit: int = 20,
        skip: int = 0
    ) -> Dict[str, Any]:
        """
        List files
        
        Args:
            collection: Filter by collection (optional)
            limit: Number of files to return
            skip: Number of files to skip (pagination)
            
        Returns:
            List of files with metadata
            
        Example:
            >>> # List all files
            >>> result = storage.files.list()
            >>> for file in result["files"]:
            ...     print(f"{file['filename']}: {file['size']} bytes")
            
            >>> # List files in specific collection
            >>> result = storage.files.list(collection="profile_images")
        """
        
        params = {
            "limit": limit,
            "skip": skip
        }
        
        if collection:
            params["collection"] = collection
        
        return self.client.get("/api/files/files", params=params)
    
    def upload_image(
        self,
        file_path: Union[str, Path, BinaryIO],
        collection: str = "images",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Upload an image (convenience method)
        
        Args:
            file_path: Path to image file
            collection: Collection name (default: "images")
            **kwargs: Additional arguments for upload()
            
        Returns:
            Upload response
            
        Example:
            >>> result = storage.files.upload_image("photo.jpg")
        """
        
        return self.upload(file_path, collection, **kwargs)
    
    def upload_document(
        self,
        file_path: Union[str, Path, BinaryIO],
        collection: str = "documents",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Upload a document (convenience method)
        
        Args:
            file_path: Path to document file
            collection: Collection name (default: "documents")
            **kwargs: Additional arguments for upload()
            
        Returns:
            Upload response
            
        Example:
            >>> result = storage.files.upload_document("report.pdf")
        """
        
        return self.upload(file_path, collection, **kwargs)