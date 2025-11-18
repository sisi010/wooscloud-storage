"""
Multipart Upload Router
Upload large files in chunks with resume capability
Similar to AWS S3 Multipart Upload
"""

from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, status
from typing import Optional, List
from datetime import datetime, timedelta
from bson import ObjectId
import hashlib
import secrets

from app.middleware.auth_middleware import verify_api_key
from app.database import get_database
from app.config import settings

router = APIRouter(prefix="/multipart", tags=["Multipart Upload"])

# Minimum chunk size: 5MB (except last chunk)
MIN_CHUNK_SIZE = 5 * 1024 * 1024  # 5MB
MAX_FILE_SIZE = 5 * 1024 * 1024 * 1024 * 1024  # 5TB


@router.post("/initiate")
async def initiate_multipart_upload(
    collection: str = Form(...),
    filename: str = Form(...),
    file_size: int = Form(..., description="Total file size in bytes"),
    content_type: Optional[str] = Form("application/octet-stream"),
    chunk_size: int = Form(5242880, description="Chunk size (default 5MB)"),
    metadata: Optional[str] = Form(None, description="JSON metadata"),
    current_user: dict = Depends(verify_api_key)
):
    """
    Initiate a multipart upload
    
    Returns upload_id for subsequent chunk uploads
    
    Steps:
    1. Initiate upload → get upload_id
    2. Upload chunks → use upload_id
    3. Complete upload → finalize
    """
    
    # Validate file size
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum limit of 5TB"
        )
    
    # Validate chunk size
    if chunk_size < MIN_CHUNK_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Chunk size must be at least {MIN_CHUNK_SIZE} bytes (5MB)"
        )
    
    db = await get_database()
    
    # Generate unique upload ID
    upload_id = secrets.token_urlsafe(32)
    
    # Calculate total chunks
    total_chunks = (file_size + chunk_size - 1) // chunk_size
    
    # Create upload session
    upload_doc = {
        "upload_id": upload_id,
        "user_id": str(current_user["_id"]),
        "collection": collection,
        "filename": filename,
        "file_size": file_size,
        "content_type": content_type,
        "chunk_size": chunk_size,
        "total_chunks": total_chunks,
        "uploaded_chunks": [],
        "completed_chunks": 0,
        "status": "initiated",
        "created_at": datetime.utcnow(),
        "expires_at": datetime.utcnow() + timedelta(days=7),  # 7 days to complete
        "metadata": metadata,
        "chunks": {}  # Store chunk info {chunk_number: {etag, size}}
    }
    
    await db.multipart_uploads.insert_one(upload_doc)
    
    return {
        "success": True,
        "upload_id": upload_id,
        "chunk_size": chunk_size,
        "total_chunks": total_chunks,
        "expires_at": upload_doc["expires_at"].isoformat(),
        "message": "Multipart upload initiated. Start uploading chunks."
    }


@router.post("/upload-chunk/{upload_id}")
async def upload_chunk(
    upload_id: str,
    chunk_number: int = Form(..., ge=1),
    chunk: UploadFile = File(...),
    current_user: dict = Depends(verify_api_key)
):
    """
    Upload a single chunk
    
    Chunks are numbered starting from 1
    Each chunk must be at least 5MB (except the last chunk)
    """
    
    db = await get_database()
    
    # Get upload session
    upload_session = await db.multipart_uploads.find_one({
        "upload_id": upload_id,
        "user_id": str(current_user["_id"])
    })
    
    if not upload_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found"
        )
    
    # Check if expired
    if datetime.utcnow() > upload_session["expires_at"]:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Upload session has expired"
        )
    
    # Check if already completed
    if upload_session["status"] == "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload already completed"
        )
    
    # Validate chunk number
    if chunk_number > upload_session["total_chunks"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid chunk number. Total chunks: {upload_session['total_chunks']}"
        )
    
    # Read chunk data
    chunk_data = await chunk.read()
    chunk_size = len(chunk_data)
    
    # Validate chunk size (except last chunk)
    if chunk_number < upload_session["total_chunks"]:
        if chunk_size < MIN_CHUNK_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Chunk size must be at least {MIN_CHUNK_SIZE} bytes (5MB), except last chunk"
            )
    
    # Calculate ETag (MD5 hash)
    etag = hashlib.md5(chunk_data).hexdigest()
    
    # Store chunk in database (for small files) or R2 (for large files)
    chunk_doc = {
        "upload_id": upload_id,
        "chunk_number": chunk_number,
        "data": chunk_data,  # Store in MongoDB for demo (use R2 for production!)
        "size": chunk_size,
        "etag": etag,
        "uploaded_at": datetime.utcnow()
    }
    
    # Check if chunk already exists
    existing_chunk = await db.upload_chunks.find_one({
        "upload_id": upload_id,
        "chunk_number": chunk_number
    })
    
    if existing_chunk:
        # Update existing chunk
        await db.upload_chunks.update_one(
            {"upload_id": upload_id, "chunk_number": chunk_number},
            {"$set": chunk_doc}
        )
    else:
        # Insert new chunk
        await db.upload_chunks.insert_one(chunk_doc)
    
    # Update upload session
    chunks_info = upload_session.get("chunks", {})
    chunks_info[str(chunk_number)] = {
        "etag": etag,
        "size": chunk_size,
        "uploaded_at": datetime.utcnow().isoformat()
    }
    
    uploaded_chunks = list(set(upload_session.get("uploaded_chunks", []) + [chunk_number]))
    
    await db.multipart_uploads.update_one(
        {"upload_id": upload_id},
        {
            "$set": {
                "chunks": chunks_info,
                "uploaded_chunks": uploaded_chunks,
                "completed_chunks": len(uploaded_chunks),
                "last_updated": datetime.utcnow()
            }
        }
    )
    
    # Calculate progress
    progress = (len(uploaded_chunks) / upload_session["total_chunks"]) * 100
    
    return {
        "success": True,
        "upload_id": upload_id,
        "chunk_number": chunk_number,
        "etag": etag,
        "size": chunk_size,
        "progress": round(progress, 2),
        "completed_chunks": len(uploaded_chunks),
        "total_chunks": upload_session["total_chunks"]
    }


@router.post("/complete/{upload_id}")
async def complete_multipart_upload(
    upload_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Complete multipart upload
    
    Assembles all chunks into final file
    """
    
    db = await get_database()
    
    # Get upload session
    upload_session = await db.multipart_uploads.find_one({
        "upload_id": upload_id,
        "user_id": str(current_user["_id"])
    })
    
    if not upload_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found"
        )
    
    # Check if all chunks uploaded
    if upload_session["completed_chunks"] != upload_session["total_chunks"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Not all chunks uploaded. {upload_session['completed_chunks']}/{upload_session['total_chunks']} completed"
        )
    
    # Retrieve all chunks in order
    chunks_cursor = db.upload_chunks.find({
        "upload_id": upload_id
    }).sort("chunk_number", 1)
    
    chunks = await chunks_cursor.to_list(None)
    
    if len(chunks) != upload_session["total_chunks"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some chunks are missing"
        )
    
    # Assemble file
    file_data = b"".join([chunk["data"] for chunk in chunks])
    
    # Calculate final hash
    final_hash = hashlib.md5(file_data).hexdigest()
    
    # Create final storage document
    storage_doc = {
        "user_id": str(current_user["_id"]),
        "collection": upload_session["collection"],
        "data": {
            "filename": upload_session["filename"],
            "content_type": upload_session["content_type"],
            "size": upload_session["file_size"],
            "etag": final_hash,
            "uploaded_via": "multipart",
            "upload_id": upload_id
        },
        "file_data": file_data,  # Store in MongoDB for demo (use R2 for production!)
        "storage_type": "multipart",
        "created_at": datetime.utcnow(),
        "metadata": upload_session.get("metadata", {})
    }
    
    result = await db.storage_data.insert_one(storage_doc)
    file_id = str(result.inserted_id)
    
    # Update upload session status
    await db.multipart_uploads.update_one(
        {"upload_id": upload_id},
        {
            "$set": {
                "status": "completed",
                "file_id": file_id,
                "completed_at": datetime.utcnow(),
                "final_etag": final_hash
            }
        }
    )
    
    # Clean up chunks (optional - keep for a while for debugging)
    # await db.upload_chunks.delete_many({"upload_id": upload_id})
    
    return {
        "success": True,
        "upload_id": upload_id,
        "file_id": file_id,
        "etag": final_hash,
        "size": upload_session["file_size"],
        "message": "Multipart upload completed successfully"
    }


@router.delete("/abort/{upload_id}")
async def abort_multipart_upload(
    upload_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Abort multipart upload and clean up chunks
    """
    
    db = await get_database()
    
    # Get upload session
    upload_session = await db.multipart_uploads.find_one({
        "upload_id": upload_id,
        "user_id": str(current_user["_id"])
    })
    
    if not upload_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found"
        )
    
    # Delete chunks
    await db.upload_chunks.delete_many({"upload_id": upload_id})
    
    # Delete upload session
    await db.multipart_uploads.delete_one({"upload_id": upload_id})
    
    return {
        "success": True,
        "message": "Multipart upload aborted and cleaned up"
    }


@router.get("/status/{upload_id}")
async def get_upload_status(
    upload_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get status of multipart upload
    """
    
    db = await get_database()
    
    upload_session = await db.multipart_uploads.find_one({
        "upload_id": upload_id,
        "user_id": str(current_user["_id"])
    })
    
    if not upload_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Upload session not found"
        )
    
    progress = (upload_session["completed_chunks"] / upload_session["total_chunks"]) * 100
    
    # Get missing chunks
    uploaded = set(upload_session["uploaded_chunks"])
    all_chunks = set(range(1, upload_session["total_chunks"] + 1))
    missing = sorted(list(all_chunks - uploaded))
    
    return {
        "success": True,
        "upload_id": upload_id,
        "filename": upload_session["filename"],
        "status": upload_session["status"],
        "progress": round(progress, 2),
        "completed_chunks": upload_session["completed_chunks"],
        "total_chunks": upload_session["total_chunks"],
        "missing_chunks": missing[:10],  # Show first 10 missing
        "created_at": upload_session["created_at"].isoformat(),
        "expires_at": upload_session["expires_at"].isoformat(),
        "is_expired": datetime.utcnow() > upload_session["expires_at"]
    }


@router.get("/list")
async def list_uploads(
    status: Optional[str] = None,
    limit: int = 20,
    current_user: dict = Depends(verify_api_key)
):
    """
    List all multipart uploads for user
    """
    
    db = await get_database()
    
    query = {"user_id": str(current_user["_id"])}
    if status:
        query["status"] = status
    
    cursor = db.multipart_uploads.find(query).sort("created_at", -1).limit(limit)
    uploads = await cursor.to_list(None)
    
    result = []
    for upload in uploads:
        progress = (upload["completed_chunks"] / upload["total_chunks"]) * 100
        result.append({
            "upload_id": upload["upload_id"],
            "filename": upload["filename"],
            "status": upload["status"],
            "progress": round(progress, 2),
            "file_size": upload["file_size"],
            "created_at": upload["created_at"].isoformat(),
            "expires_at": upload["expires_at"].isoformat()
        })
    
    return {
        "success": True,
        "total": len(result),
        "uploads": result
    }