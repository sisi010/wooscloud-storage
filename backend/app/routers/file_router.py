"""
File router
Handles file upload/download operations with Webhook support
"""

from fastapi import APIRouter, HTTPException, status, Depends, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import Optional
import io
import json
import logging

from app.models.file_data import FileUploadResponse, FileInfo
from app.services.file_storage import FileStorageService
from app.middleware.auth_middleware import verify_api_key
from app.services.quota_manager import (
    check_storage_quota,
    check_api_calls_quota,
    increment_api_calls,
    update_storage_usage
)
from app.database import get_database
from app.services.webhook_service import WebhookService

logger = logging.getLogger(__name__)
router = APIRouter()

# R2 storage will be set by main.py
r2_storage = None

def get_file_storage_service() -> FileStorageService:
    """Get file storage service instance with R2"""
    return FileStorageService(r2_storage=r2_storage)

@router.post("/upload", response_model=FileUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_file(
    file: UploadFile = File(...),
    collection: str = Form(...),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),  # JSON string
    custom_metadata: Optional[str] = Form(None),  # JSON string
    current_user: dict = Depends(verify_api_key),
    file_service: FileStorageService = Depends(get_file_storage_service)
):
    """
    Upload a file
    
    - Automatically routes to MongoDB (< 5MB) or R2 (≥ 5MB)
    - Supports any file type
    - Maximum file size: 100MB (free tier)
    """
    
    # Check API calls quota
    await check_api_calls_quota(current_user["_id"])
    
    try:
        # Read file content
        file_content = await file.read()
        file_size = len(file_content)
        
        # Check storage quota
        await check_storage_quota(current_user["_id"], file_size)
        
        # Parse metadata
        metadata = {}
        if description:
            metadata["description"] = description
        if tags:
            try:
                metadata["tags"] = json.loads(tags)
            except:
                metadata["tags"] = [t.strip() for t in tags.split(",")]
        if custom_metadata:
            try:
                metadata["custom"] = json.loads(custom_metadata)
            except:
                pass
        
        # Upload file
        result = await file_service.upload_file(
            file_content=file_content,
            filename=file.filename,
            content_type=file.content_type or "application/octet-stream",
            collection=collection,
            user_id=current_user["_id"],
            metadata=metadata
        )
        
        file_id = result["id"]
        storage_type = result["storage_type"]
        
        # Update storage usage
        await update_storage_usage(current_user["_id"], file_size)
        
        # Increment API calls
        await increment_api_calls(current_user["_id"])
        
        # Trigger webhook
        try:
            db = await get_database()
            webhook_service = WebhookService(db)
            await webhook_service.trigger_event(
                user_id=str(current_user["_id"]),
                event="file.uploaded",
                payload={
                    "id": file_id,
                    "filename": result["filename"],
                    "collection": collection,
                    "size": file_size,
                    "storage_type": storage_type,
                    "content_type": file.content_type or "application/octet-stream"
                }
            )
        except Exception as e:
            logger.warning(f"Failed to trigger webhook: {e}")
        
        return FileUploadResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )

@router.get("/download/{file_id}")
async def download_file(
    file_id: str,
    current_user: dict = Depends(verify_api_key),
    file_service: FileStorageService = Depends(get_file_storage_service)
):
    """
    Download a file
    
    - Retrieves file from MongoDB or R2
    - Returns file with proper content type
    - Supports streaming for large files
    """
    
    # Check API calls quota
    await check_api_calls_quota(current_user["_id"])
    
    try:
        # Download file
        file_data = await file_service.download_file(
            file_id=file_id,
            user_id=current_user["_id"]
        )
        
        # Increment API calls
        await increment_api_calls(current_user["_id"])
        
        # Return file as streaming response
        return StreamingResponse(
            io.BytesIO(file_data["content"]),
            media_type=file_data["content_type"],
            headers={
                "Content-Disposition": f'attachment; filename="{file_data["filename"]}"',
                "Content-Length": str(file_data["size"])
            }
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to download file: {str(e)}"
        )

@router.get("/file/{file_id}", response_model=FileInfo)
async def get_file_info(
    file_id: str,
    current_user: dict = Depends(verify_api_key),
    file_service: FileStorageService = Depends(get_file_storage_service)
):
    """
    Get file information without downloading
    
    - Returns metadata, size, storage location
    - Does not count towards storage quota
    """
    
    # Check API calls quota
    await check_api_calls_quota(current_user["_id"])
    
    try:
        # Get file info
        file_info = await file_service.get_file_info(
            file_id=file_id,
            user_id=current_user["_id"]
        )
        
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Increment API calls
        await increment_api_calls(current_user["_id"])
        
        return FileInfo(**file_info)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get file info: {str(e)}"
        )

@router.delete("/file/{file_id}")
async def delete_file(
    file_id: str,
    current_user: dict = Depends(verify_api_key),
    file_service: FileStorageService = Depends(get_file_storage_service)
):
    """
    Delete a file
    
    - Removes file from storage (MongoDB or R2)
    - Frees up storage quota
    """
    
    # Check API calls quota
    await check_api_calls_quota(current_user["_id"])
    
    try:
        # Get file info first to update quota
        file_info = await file_service.get_file_info(
            file_id=file_id,
            user_id=current_user["_id"]
        )
        
        if not file_info:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Delete file
        success = await file_service.delete_file(
            file_id=file_id,
            user_id=current_user["_id"]
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="File not found"
            )
        
        # Update storage usage (decrease)
        await update_storage_usage(current_user["_id"], -file_info["size"])
        
        # Increment API calls
        await increment_api_calls(current_user["_id"])
        
        return {
            "success": True,
            "message": "File deleted successfully",
            "id": file_id,
            "freed_bytes": file_info["size"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}"
        )

@router.get("/files")
async def list_files(
    collection: Optional[str] = None,
    limit: int = 20,
    skip: int = 0,
    current_user: dict = Depends(verify_api_key)
):
    """
    List user's files
    
    - Filter by collection (optional)
    - Paginated results
    """
    
    # Check API calls quota
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        
        # Build query
        query = {"user_id": current_user["_id"]}
        if collection:
            query["collection"] = collection
        
        # Get files
        cursor = db.files.find(
            query,
            {"content": 0}  # Exclude content
        ).sort("created_at", -1).skip(skip).limit(limit)
        
        files = await cursor.to_list(length=limit)
        
        # Get total count
        total = await db.files.count_documents(query)
        
        # Format response
        result = []
        for file_doc in files:
            result.append({
                "id": file_doc["_id"],
                "filename": file_doc["filename"],
                "content_type": file_doc["content_type"],
                "size": file_doc["size"],
                "storage_type": file_doc["storage_type"],
                "collection": file_doc["collection"],
                "metadata": file_doc.get("metadata", {}),
                "url": file_doc.get("r2_url"),
                "created_at": file_doc["created_at"].isoformat()
            })
        
        # Increment API calls
        await increment_api_calls(current_user["_id"])
        
        return {
            "success": True,
            "files": result,
            "total": total,
            "limit": limit,
            "skip": skip
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list files: {str(e)}"
        )