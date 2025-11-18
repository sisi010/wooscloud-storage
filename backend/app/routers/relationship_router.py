"""
Relationship Router
API endpoints for data relationship management
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query, Header
from typing import Optional, List
from bson import ObjectId

from app.models.relationship_models import (
    RelationshipCreate, RelationshipUpdate, Relationship,
    RelationshipListResponse, RelationshipStats,
    RELATIONSHIP_EXAMPLES, RelationshipExamplesResponse
)
from app.middleware.auth_middleware import verify_api_key
from app.database import get_database
from app.services.relationship_service import RelationshipService
from app.services.quota_manager import check_api_calls_quota, increment_api_calls

router = APIRouter()

# ============================================================================
# POPULATE (Must be FIRST - before /{relationship_id})
# ============================================================================

@router.get("/relationships/populate/{document_id}")
async def populate_document(
    document_id: str,
    collection: str = Query(..., description="Collection name"),
    fields: List[str] = Query(..., description="Fields to populate"),
    depth: int = Query(1, ge=1, le=3, description="Population depth"),
    current_user: dict = Depends(verify_api_key),
    x_api_key: str = Header(..., alias="X-API-Key")
):
    """
    Get document with populated references
    """
    
    import logging
    from bson import ObjectId
    logger = logging.getLogger(__name__)
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        rel_service = RelationshipService(db)
        
        # Get original document via Storage API
        logger.info(f"Getting document via Storage API: {document_id}")
        
        # Use the API key from current request
        logger.info(f"Using API key from request: {x_api_key[:10]}...")
        
        import httpx
        async with httpx.AsyncClient() as client:
            storage_response = await client.get(
                f"http://127.0.0.1:8000/api/storage/read/{document_id}",
                headers={"X-API-Key": x_api_key},
                params={"collection": collection}
            )
            
            result = storage_response.json()
            doc = result.get("data", {})
            doc["_id"] = document_id  # Add _id for compatibility
        
        logger.info(f"Document found: {doc is not None}")
        
        # DEBUG: Try without user_id filter
        if not doc:
            logger.warning(f"Trying WITHOUT user_id filter...")
            
            # Check what's actually in the database
            logger.info(f"Database name: {db.name}")
            logger.info(f"Collection name: {collection}")
            
            # Count total documents in collection
            count = await db[collection].count_documents({})
            logger.info(f"Total documents in {collection}: {count}")
            
            # Try to find ANY document
            sample = await db[collection].find_one({})
            if sample:
                logger.info(f"Sample document found: _id={sample.get('_id')}, user_id={sample.get('user_id')}")
            
            try:
                doc_no_filter = await db[collection].find_one({"_id": ObjectId(document_id)})
                if not doc_no_filter:
                    doc_no_filter = await db[collection].find_one({"_id": document_id})
                
                if doc_no_filter:
                    logger.error(f"Document EXISTS but user_id mismatch!")
                    logger.error(f"Document user_id: {doc_no_filter.get('user_id')}")
                    logger.error(f"Current user_id: {str(current_user['_id'])}")
                else:
                    logger.error(f"Document does NOT exist in collection!")
            except Exception as e:
                logger.error(f"Debug search failed: {e}")
        
        if not doc:
            logger.error(f"Document not found!")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found in {collection}"
            )
        
        logger.info(f"Document found! Keys: {doc.keys()}")
        
        # Convert ObjectId
        doc["id"] = str(doc.pop("_id"))
        
        # Pass API key to service
        rel_service._api_key = x_api_key
        
        logger.info(f"Set API key in service: {x_api_key[:10]}...")
        
        # Populate
        populated = await rel_service.populate_document(
            user_id=str(current_user["_id"]),
            collection=collection,
            document=doc,
            populate_fields=fields,
            depth=depth
        )
        
        await increment_api_calls(current_user["_id"])
        
        return {
            "id": document_id,
            "collection": collection,
            "data": populated,
            "populated_fields": fields
        }
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"Populate error: {error_details}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to populate document: {str(e)}"
        )


# ============================================================================
# EXAMPLES (Must be before /{relationship_id})
# ============================================================================

@router.get("/relationships/examples/list", response_model=RelationshipExamplesResponse)
async def get_relationship_examples(
    current_user: dict = Depends(verify_api_key)
):
    """Get example relationship configurations"""
    
    await check_api_calls_quota(current_user["_id"])
    await increment_api_calls(current_user["_id"])
    
    return RelationshipExamplesResponse(examples=RELATIONSHIP_EXAMPLES)


# ============================================================================
# VALIDATION (Must be before /{relationship_id})
# ============================================================================

@router.post("/relationships/validate")
async def validate_references(
    collection: str = Query(..., description="Collection name"),
    document: dict = ...,
    current_user: dict = Depends(verify_api_key),
    x_api_key: str = Header(..., alias="X-API-Key")
):
    """Validate all references in a document"""
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        rel_service = RelationshipService(db)
        
        # Pass API key to service
        rel_service._api_key = x_api_key
        
        validation = await rel_service.validate_references(
            user_id=str(current_user["_id"]),
            collection=collection,
            document=document
        )
        
        await increment_api_calls(current_user["_id"])
        
        return validation
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to validate references: {str(e)}"
        )


# ============================================================================
# RELATIONSHIPS
# ============================================================================

@router.post("/relationships", response_model=Relationship, status_code=status.HTTP_201_CREATED)
async def create_relationship(
    request: RelationshipCreate,
    current_user: dict = Depends(verify_api_key)
):
    """Create a relationship between collections"""
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        rel_service = RelationshipService(db)
        
        relationship = await rel_service.create_relationship(
            user_id=str(current_user["_id"]),
            request=request
        )
        
        await increment_api_calls(current_user["_id"])
        
        return relationship
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create relationship: {str(e)}"
        )


@router.get("/relationships", response_model=RelationshipListResponse)
async def list_relationships(
    from_collection: Optional[str] = Query(None, description="Filter by source collection"),
    to_collection: Optional[str] = Query(None, description="Filter by target collection"),
    current_user: dict = Depends(verify_api_key)
):
    """List all relationships"""
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        rel_service = RelationshipService(db)
        
        relationships = await rel_service.list_relationships(
            user_id=str(current_user["_id"]),
            from_collection=from_collection,
            to_collection=to_collection
        )
        
        await increment_api_calls(current_user["_id"])
        
        return RelationshipListResponse(
            relationships=relationships,
            total=len(relationships)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list relationships: {str(e)}"
        )


@router.get("/relationships/{relationship_id}", response_model=Relationship)
async def get_relationship(
    relationship_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """Get relationship by ID"""
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        rel_service = RelationshipService(db)
        
        relationship = await rel_service.get_relationship(
            rel_id=relationship_id,
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        if not relationship:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Relationship {relationship_id} not found"
            )
        
        return relationship
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get relationship: {str(e)}"
        )


@router.patch("/relationships/{relationship_id}", response_model=Relationship)
async def update_relationship(
    relationship_id: str,
    request: RelationshipUpdate,
    current_user: dict = Depends(verify_api_key)
):
    """Update relationship"""
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        rel_service = RelationshipService(db)
        
        relationship = await rel_service.update_relationship(
            rel_id=relationship_id,
            user_id=str(current_user["_id"]),
            request=request
        )
        
        await increment_api_calls(current_user["_id"])
        
        return relationship
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update relationship: {str(e)}"
        )


@router.delete("/relationships/{relationship_id}")
async def delete_relationship(
    relationship_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """Delete relationship"""
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        rel_service = RelationshipService(db)
        
        deleted = await rel_service.delete_relationship(
            rel_id=relationship_id,
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Relationship {relationship_id} not found"
            )
        
        return {
            "message": "Relationship deleted successfully",
            "relationship_id": relationship_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete relationship: {str(e)}"
        )


# ============================================================================
# STATISTICS
# ============================================================================

@router.get("/relationships/{relationship_id}/stats", response_model=RelationshipStats)
async def get_relationship_stats(
    relationship_id: str,
    current_user: dict = Depends(verify_api_key)
):
    """Get relationship statistics"""
    
    await check_api_calls_quota(current_user["_id"])
    
    try:
        db = await get_database()
        rel_service = RelationshipService(db)
        
        stats = await rel_service.get_relationship_stats(
            rel_id=relationship_id,
            user_id=str(current_user["_id"])
        )
        
        await increment_api_calls(current_user["_id"])
        
        return stats
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get statistics: {str(e)}"
        )