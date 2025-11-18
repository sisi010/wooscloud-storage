"""
File Preview Router
Generate thumbnails and previews for images, PDFs, and documents
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Response, status
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime
from bson import ObjectId
from PIL import Image
import io
import base64

from app.middleware.auth_middleware import verify_api_key
from app.database import get_database

router = APIRouter(prefix="/preview", tags=["File Preview"])

# Supported file types
PREVIEW_SUPPORTED = {
    "image": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"],
    "pdf": [".pdf"],
    "text": [".txt", ".md", ".json", ".xml", ".csv"]
}


@router.get("/thumbnail/{data_id}")
async def generate_thumbnail(
    data_id: str,
    width: int = Query(200, ge=50, le=1000, description="Thumbnail width"),
    height: int = Query(200, ge=50, le=1000, description="Thumbnail height"),
    format: str = Query("png", description="Output format: png, jpg, webp"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Generate thumbnail for image files
    
    Supported formats: JPG, PNG, GIF, WebP, BMP
    """
    
    db = await get_database()
    
    # Get data
    try:
        data_object_id = ObjectId(data_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data ID"
        )
    
    doc = await db.storage_data.find_one({
        "_id": data_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )
    
    # Check if image file
    filename = doc.get("data", {}).get("filename", "")
    if not any(filename.lower().endswith(ext) for ext in PREVIEW_SUPPORTED["image"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not an image"
        )
    
    # Get file data
    file_data = doc.get("file_data")
    if not file_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File data not found"
        )
    
    try:
        # Open image
        image = Image.open(io.BytesIO(file_data))
        
        # Generate thumbnail
        image.thumbnail((width, height), Image.Resampling.LANCZOS)
        
        # Save to bytes
        output = io.BytesIO()
        
        if format.lower() == "jpg" or format.lower() == "jpeg":
            # Convert RGBA to RGB for JPEG
            if image.mode == "RGBA":
                rgb_image = Image.new("RGB", image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[3])
                image = rgb_image
            image.save(output, format="JPEG", quality=85)
            media_type = "image/jpeg"
        elif format.lower() == "webp":
            image.save(output, format="WebP", quality=85)
            media_type = "image/webp"
        else:
            image.save(output, format="PNG")
            media_type = "image/png"
        
        output.seek(0)
        
        # Cache thumbnail
        thumbnail_doc = {
            "data_id": data_id,
            "user_id": str(current_user["_id"]),
            "width": width,
            "height": height,
            "format": format,
            "thumbnail_data": output.getvalue(),
            "created_at": datetime.utcnow()
        }
        
        # Check if thumbnail already exists
        existing = await db.thumbnails.find_one({
            "data_id": data_id,
            "width": width,
            "height": height,
            "format": format
        })
        
        if existing:
            await db.thumbnails.update_one(
                {"_id": existing["_id"]},
                {"$set": thumbnail_doc}
            )
        else:
            await db.thumbnails.insert_one(thumbnail_doc)
        
        return StreamingResponse(
            io.BytesIO(output.getvalue()),
            media_type=media_type,
            headers={
                "Content-Disposition": f"inline; filename=thumbnail_{data_id}.{format}"
            }
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate thumbnail: {str(e)}"
        )


@router.get("/image/{data_id}")
async def preview_image(
    data_id: str,
    max_width: int = Query(1920, ge=100, le=4096),
    max_height: int = Query(1080, ge=100, le=4096),
    current_user: dict = Depends(verify_api_key)
):
    """
    Get optimized image preview
    Resizes large images for faster loading
    """
    
    db = await get_database()
    
    try:
        data_object_id = ObjectId(data_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data ID"
        )
    
    doc = await db.storage_data.find_one({
        "_id": data_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )
    
    file_data = doc.get("file_data")
    if not file_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File data not found"
        )
    
    try:
        image = Image.open(io.BytesIO(file_data))
        
        # Resize if too large
        if image.width > max_width or image.height > max_height:
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        
        output = io.BytesIO()
        
        # Determine format
        format_map = {
            "JPEG": "JPEG",
            "PNG": "PNG",
            "GIF": "GIF",
            "WEBP": "WebP"
        }
        
        save_format = format_map.get(image.format, "PNG")
        
        if save_format == "JPEG":
            if image.mode == "RGBA":
                rgb_image = Image.new("RGB", image.size, (255, 255, 255))
                rgb_image.paste(image, mask=image.split()[3])
                image = rgb_image
            image.save(output, format="JPEG", quality=90)
            media_type = "image/jpeg"
        else:
            image.save(output, format=save_format)
            media_type = f"image/{save_format.lower()}"
        
        output.seek(0)
        
        return StreamingResponse(
            output,
            media_type=media_type
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to preview image: {str(e)}"
        )


@router.get("/text/{data_id}")
async def preview_text(
    data_id: str,
    max_lines: int = Query(100, ge=10, le=1000),
    current_user: dict = Depends(verify_api_key)
):
    """
    Preview text files
    Returns first N lines
    """
    
    db = await get_database()
    
    try:
        data_object_id = ObjectId(data_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data ID"
        )
    
    doc = await db.storage_data.find_one({
        "_id": data_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )
    
    file_data = doc.get("file_data")
    if not file_data:
        # Try to get from data field
        data_content = doc.get("data", {})
        if isinstance(data_content, str):
            file_data = data_content.encode('utf-8')
        elif isinstance(data_content, dict):
            import json
            file_data = json.dumps(data_content, indent=2).encode('utf-8')
    
    if not file_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File data not found"
        )
    
    try:
        # Decode text
        text = file_data.decode('utf-8')
        
        # Split by lines
        lines = text.split('\n')
        
        # Limit lines
        preview_lines = lines[:max_lines]
        truncated = len(lines) > max_lines
        
        return {
            "success": True,
            "data_id": data_id,
            "total_lines": len(lines),
            "preview_lines": len(preview_lines),
            "truncated": truncated,
            "content": '\n'.join(preview_lines)
        }
        
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is not a text file"
        )


@router.get("/metadata/{data_id}")
async def get_file_metadata(
    data_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get file metadata including dimensions, size, type, etc.
    """
    
    db = await get_database()
    
    try:
        data_object_id = ObjectId(data_id)
    except:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid data ID"
        )
    
    doc = await db.storage_data.find_one({
        "_id": data_object_id,
        "user_id": str(current_user["_id"])
    })
    
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Data not found"
        )
    
    metadata = {
        "id": str(doc["_id"]),
        "filename": doc.get("data", {}).get("filename"),
        "content_type": doc.get("data", {}).get("content_type"),
        "size": doc.get("data", {}).get("size"),
        "created_at": doc.get("created_at").isoformat() if doc.get("created_at") else None
    }
    
    # Try to get image dimensions
    file_data = doc.get("file_data")
    if file_data:
        try:
            image = Image.open(io.BytesIO(file_data))
            metadata["image"] = {
                "width": image.width,
                "height": image.height,
                "format": image.format,
                "mode": image.mode
            }
        except:
            pass
    
    return {
        "success": True,
        "metadata": metadata
    }


@router.get("/supported-types")
async def get_supported_types():
    """
    Get list of supported file types for preview
    """
    
    return {
        "success": True,
        "supported_types": PREVIEW_SUPPORTED,
        "total_types": sum(len(v) for v in PREVIEW_SUPPORTED.values())
    }


@router.delete("/cache/{data_id}")
async def clear_preview_cache(
    data_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Clear cached thumbnails and previews for a file
    """
    
    db = await get_database()
    
    result = await db.thumbnails.delete_many({
        "data_id": data_id,
        "user_id": str(current_user["_id"])
    })
    
    return {
        "success": True,
        "deleted": result.deleted_count,
        "message": "Preview cache cleared"
    }


@router.get("/batch-thumbnails")
async def batch_generate_thumbnails(
    data_ids: str = Query(..., description="Comma-separated data IDs"),
    width: int = Query(200),
    height: int = Query(200),
    current_user: dict = Depends(verify_api_key)
):
    """
    Generate thumbnails for multiple files
    Returns base64 encoded thumbnails
    """
    
    ids = data_ids.split(',')
    
    if len(ids) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 20 files at once"
        )
    
    db = await get_database()
    results = []
    
    for data_id in ids:
        try:
            data_object_id = ObjectId(data_id.strip())
            
            doc = await db.storage_data.find_one({
                "_id": data_object_id,
                "user_id": str(current_user["_id"])
            })
            
            if not doc or not doc.get("file_data"):
                results.append({
                    "data_id": data_id,
                    "success": False,
                    "error": "Not found"
                })
                continue
            
            # Generate thumbnail
            image = Image.open(io.BytesIO(doc["file_data"]))
            image.thumbnail((width, height), Image.Resampling.LANCZOS)
            
            output = io.BytesIO()
            image.save(output, format="PNG")
            output.seek(0)
            
            # Convert to base64
            thumbnail_base64 = base64.b64encode(output.getvalue()).decode('utf-8')
            
            results.append({
                "data_id": data_id,
                "success": True,
                "thumbnail": f"data:image/png;base64,{thumbnail_base64}",
                "width": image.width,
                "height": image.height
            })
            
        except Exception as e:
            results.append({
                "data_id": data_id,
                "success": False,
                "error": str(e)
            })
    
    return {
        "success": True,
        "total": len(results),
        "thumbnails": results
    }