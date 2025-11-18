"""
Encryption Router
API endpoints for data encryption management

FIXED VERSION - Matches storage_router.py pattern exactly
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional
import logging

from app.models.encryption_models import (
    EncryptFieldRequest,
    EncryptFieldResponse,
    DecryptFieldRequest,
    EncryptionConfig,
    EncryptionStats
)
from app.middleware.auth_middleware import verify_api_key
from app.database import get_database
from app.services.encryption_service import get_encryption_service
from app.services.quota_manager import check_api_calls_quota, increment_api_calls
from bson import ObjectId

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/encryption")

@router.post("/encrypt", response_model=EncryptFieldResponse)
async def encrypt_document_fields(
    request: EncryptFieldRequest,
    current_user: dict = Depends(verify_api_key)
):
    """
    Encrypt specific fields in a document
    
    **Encrypts sensitive data at rest using AES-256-GCM**
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        
        # Convert string ID to ObjectId
        try:
            data_object_id = ObjectId(request.document_id)
        except:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document ID format"
            )
        
        # FIXED: Use storage_data collection and match storage_router.py pattern
        doc = await db.storage_data.find_one({
            "_id": data_object_id,
            "user_id": str(current_user["_id"])  # user_id is stored as string
        })

        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check if document belongs to requested collection
        if doc.get("collection") != request.collection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document does not belong to collection '{request.collection}'"
            )
        
        # Get the actual data
        # For MongoDB storage, data is in 'data' field
        # For R2 storage, we need to fetch it separately
        storage_type = doc.get("storage_type", "mongodb")
        
        if storage_type == "mongodb":
            data = doc.get("data", {})
        else:
            # R2 storage - data not in document, skip encryption for now
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Encryption not supported for R2-stored data yet"
            )
        
        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document has no data to encrypt"
            )
        
        # Verify fields exist before encrypting
        missing_fields = [f for f in request.fields if f not in data]
        if missing_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Fields not found in document: {', '.join(missing_fields)}"
            )
        
        # Encrypt fields
        encryption_service = get_encryption_service()
        encrypted_data = encryption_service.encrypt_dict(
            data=data,
            user_id=str(current_user["_id"]),
            fields_to_encrypt=request.fields
        )
        
        # Update document - only update the data field
        await db.storage_data.update_one(
            {"_id": data_object_id},
            {"$set": {"data": encrypted_data}}
        )
        
        await increment_api_calls(current_user["_id"])
        
        logger.info(f"Encrypted {len(request.fields)} field(s) in document {request.document_id}")
        
        return EncryptFieldResponse(
            success=True,
            document_id=request.document_id,
            encrypted_fields=request.fields,
            message=f"Successfully encrypted {len(request.fields)} field(s)"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to encrypt fields: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to encrypt fields: {str(e)}"
        )

@router.post("/decrypt")
async def decrypt_document_fields(
    request: DecryptFieldRequest,
    current_user: dict = Depends(verify_api_key)
):
    """
    Decrypt specific fields in a document
    
    **Decrypts data that was encrypted at rest**
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        
        # Convert string ID to ObjectId
        try:
            data_object_id = ObjectId(request.document_id)
        except:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid document ID format"
            )
        
        # FIXED: Use storage_data collection and match storage_router.py pattern
        doc = await db.storage_data.find_one({
            "_id": data_object_id,
            "user_id": str(current_user["_id"])  # user_id is stored as string
        })
        
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Check if document belongs to requested collection
        if doc.get("collection") != request.collection:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Document does not belong to collection '{request.collection}'"
            )
        
        # Get the actual data
        storage_type = doc.get("storage_type", "mongodb")
        
        if storage_type == "mongodb":
            data = doc.get("data", {})
        else:
            # R2 storage - data not in document
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Decryption not supported for R2-stored data yet"
            )
        
        if not data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document has no data to decrypt"
            )
        
        # Decrypt fields
        encryption_service = get_encryption_service()
        decrypted_data = encryption_service.decrypt_dict(
            data=data,
            user_id=str(current_user["_id"]),
            fields_to_decrypt=request.fields
        )
        
        await increment_api_calls(current_user["_id"])
        
        logger.info(f"Decrypted fields in document {request.document_id}")
        
        return {
            "success": True,
            "document_id": request.document_id,
            "collection": request.collection,
            "data": decrypted_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to decrypt fields: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to decrypt fields: {str(e)}"
        )


@router.get("/config/{collection}")
async def get_encryption_config(
    collection: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Get encryption configuration for a collection
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        config_collection = db["encryption_configs"]
        
        config = await config_collection.find_one({
            "user_id": str(current_user["_id"]),
            "collection": collection
        })
        
        if not config:
            return {
                "collection": collection,
                "fields": [],
                "enabled": False
            }
        
        # Convert ObjectId
        config["id"] = str(config.pop("_id"))
        
        await increment_api_calls(current_user["_id"])
        
        return config
        
    except Exception as e:
        logger.error(f"Failed to get encryption config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get encryption config: {str(e)}"
        )


@router.post("/config", response_model=EncryptionConfig)
async def set_encryption_config(
    config: EncryptionConfig,
    current_user: dict = Depends(verify_api_key)
):
    """
    Set encryption configuration for a collection
    
    **Configure which fields should be automatically encrypted**
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        config_collection = db["encryption_configs"]
        
        # Upsert configuration
        await config_collection.update_one(
            {
                "user_id": str(current_user["_id"]),
                "collection": config.collection
            },
            {
                "$set": {
                    "user_id": str(current_user["_id"]),
                    "collection": config.collection,
                    "fields": config.fields,
                    "enabled": config.enabled
                }
            },
            upsert=True
        )
        
        await increment_api_calls(current_user["_id"])
        
        logger.info(f"Set encryption config for collection '{config.collection}'")
        
        return config
        
    except Exception as e:
        logger.error(f"Failed to set encryption config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set encryption config: {str(e)}"
        )


@router.get("/stats", response_model=EncryptionStats)
async def get_encryption_stats(
    current_user: dict = Depends(verify_api_key)
):
    """
    Get encryption statistics for the user
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        
        # Get all encryption configs
        config_collection = db["encryption_configs"]
        configs = await config_collection.find({
            "user_id": str(current_user["_id"]),
            "enabled": True
        }).to_list(None)
        
        # Calculate stats
        total_fields = sum(len(c.get("fields", [])) for c in configs)
        collections = [c["collection"] for c in configs]
        
        await increment_api_calls(current_user["_id"])
        
        return EncryptionStats(
            total_encrypted_fields=total_fields,
            collections_with_encryption=collections,
            encryption_enabled=len(configs) > 0,
            last_encryption=None
        )
        
    except Exception as e:
        logger.error(f"Failed to get encryption stats: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get encryption stats: {str(e)}"
        )


@router.delete("/config/{collection}")
async def delete_encryption_config(
    collection: str,
    current_user: dict = Depends(verify_api_key)
):
    """
    Delete encryption configuration for a collection
    """
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        config_collection = db["encryption_configs"]
        
        result = await config_collection.delete_one({
            "user_id": str(current_user["_id"]),
            "collection": collection
        })
        
        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Encryption config not found"
            )
        
        await increment_api_calls(current_user["_id"])
        
        logger.info(f"Deleted encryption config for collection '{collection}'")
        
        return {
            "success": True,
            "message": f"Encryption config deleted for {collection}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete encryption config: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete encryption config: {str(e)}"
        )