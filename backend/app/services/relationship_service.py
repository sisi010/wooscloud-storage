"""
Relationship Service
Data relationships with automatic population and cascade operations
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
import logging

from app.models.relationship_models import (
    RelationType, CascadeAction,
    RelationshipCreate, RelationshipUpdate, Relationship,
    PopulateOptions, CascadeResult,
    ReferenceValidationResult, BulkReferenceValidation,
    RelationshipStats, RelationshipHealthStatus
)

logger = logging.getLogger(__name__)

# ============================================================================
# CACHING CLASSES
# ============================================================================

class RelationshipCache:
    """Simple in-memory cache for relationships"""
    
    def __init__(self, ttl_seconds: int = 300):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, key: str):
        """Get cached value if not expired"""
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, value):
        """Set cached value with timestamp"""
        self.cache[key] = (value, datetime.now())
    
    def invalidate(self, pattern: str = None):
        """Invalidate cache entries"""
        if pattern:
            keys_to_delete = [k for k in self.cache.keys() if pattern in k]
            for k in keys_to_delete:
                del self.cache[k]
        else:
            self.cache.clear()


class DocumentCache:
    """Cache for fetched documents"""
    
    def __init__(self, ttl_seconds: int = 60):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get(self, collection: str, doc_id: str):
        """Get cached document"""
        key = f"{collection}:{doc_id}"
        if key in self.cache:
            value, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl):
                return value
            else:
                del self.cache[key]
        return None
    
    def set(self, collection: str, doc_id: str, value):
        """Set cached document"""
        key = f"{collection}:{doc_id}"
        self.cache[key] = (value, datetime.now())



class RelationshipService:
    """
    Relationship Service
    
    Features:
    - Define relationships between collections
    - Automatic reference population
    - Cascade operations (delete, update)
    - Reference validation
    - Relationship health monitoring
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.relationships = db.relationships

        self.cache = RelationshipCache(ttl_seconds=300)
        self.doc_cache = DocumentCache(ttl_seconds=60)
    # ========================================================================
    # RELATIONSHIP MANAGEMENT
    # ========================================================================
    
    async def create_relationship(
        self,
        user_id: str,
        request: RelationshipCreate
    ) -> Relationship:
        """Create a new relationship definition"""
        
        # Check if relationship already exists
        existing = await self.relationships.find_one({
            "user_id": user_id,
            "name": request.name
        })
        
        if existing:
            raise ValueError(f"Relationship '{request.name}' already exists")
        
        # Validate collections exist (optional - collections created on demand)
        
        rel_id = str(ObjectId())
        now = datetime.utcnow()
        
        rel_doc = {
            "_id": rel_id,
            "user_id": user_id,
            "name": request.name,
            "from_collection": request.from_collection,
            "to_collection": request.to_collection,
            "relation_type": request.relation_type.value,
            "from_field": request.from_field,
            "to_field": request.to_field,
            "on_delete": request.on_delete.value,
            "on_update": request.on_update.value,
            "required": request.required,
            "description": request.description,
            "tags": request.tags,
            "created_at": now,
            "updated_at": now
        }
        
        await self.relationships.insert_one(rel_doc)
        
        return await self.get_relationship(rel_id, user_id)
    
    async def get_relationship(
        self,
        rel_id: str,
        user_id: str
    ) -> Optional[Relationship]:
        """Get relationship by ID"""
        
        rel = await self.relationships.find_one({
            "_id": rel_id,
            "user_id": user_id
        })
        
        if not rel:
            return None
        
        return self._doc_to_relationship(rel)
    
    async def list_relationships(
        self,
        user_id: str,
        from_collection: Optional[str] = None,
        to_collection: Optional[str] = None
    ) -> List[Relationship]:
        """List user's relationships"""
        
        query = {"user_id": user_id}
        
        if from_collection:
            query["from_collection"] = from_collection
        
        if to_collection:
            query["to_collection"] = to_collection
        
        rels = await self.relationships.find(query).to_list(None)
        
        return [self._doc_to_relationship(r) for r in rels]
    
    async def update_relationship(
        self,
        rel_id: str,
        user_id: str,
        request: RelationshipUpdate
    ) -> Relationship:
        """Update relationship"""
        
        rel = await self.relationships.find_one({
            "_id": rel_id,
            "user_id": user_id
        })
        
        if not rel:
            raise ValueError("Relationship not found")
        
        update_doc = {"updated_at": datetime.utcnow()}
        
        if request.name:
            update_doc["name"] = request.name
        if request.on_delete:
            update_doc["on_delete"] = request.on_delete.value
        if request.on_update:
            update_doc["on_update"] = request.on_update.value
        if request.required is not None:
            update_doc["required"] = request.required
        if request.description is not None:
            update_doc["description"] = request.description
        if request.tags is not None:
            update_doc["tags"] = request.tags
        
        await self.relationships.update_one(
            {"_id": rel_id},
            {"$set": update_doc}
        )
        
        return await self.get_relationship(rel_id, user_id)
    
    async def delete_relationship(
        self,
        rel_id: str,
        user_id: str
    ) -> bool:
        """Delete relationship definition"""
        
        result = await self.relationships.delete_one({
            "_id": rel_id,
            "user_id": user_id
        })
        
        return result.deleted_count > 0
    
    # ========================================================================
    # POPULATE (AUTO-LOAD REFERENCES)
    # ========================================================================
    
    async def populate_document(
        self,
        user_id: str,
        collection: str,
        document: Dict[str, Any],
        populate_fields: List[str],
        depth: int = 1
    ) -> Dict[str, Any]:
        """Populate referenced documents"""
        
        if depth <= 0:
            return document
        
        # Get relationships for this collection
        relationships = await self.list_relationships(
            user_id=user_id,
            from_collection=collection
        )
        
        populated = document.copy()
        
        for field in populate_fields:
            # Find relationship for this field
            rel = next((r for r in relationships if r.from_field == field), None)
            
            if not rel:
                continue
            
            if not rel:
                logger.info(f"No relationship found for field: {field}")
                continue
            
            logger.info(f"Found relationship: {rel.name} for field: {field}")
            
            # Get reference value
            ref_value = document.get(field)
            
            if not ref_value:
                logger.info(f"No reference value for field: {field}")
                continue
            
            logger.info(f"Reference value for {field}: {ref_value}")
            logger.info(f"Populating field: {field}, type: {rel.relation_type}, value: {ref_value}")
            
            # Populate based on relationship type
            if rel.relation_type == RelationType.ONE_TO_ONE:
                # Single reference
                if isinstance(ref_value, str):
                    target_doc = await self._get_referenced_doc(
                        user_id, rel.to_collection, ref_value,
                        api_key=getattr(self, '_api_key', None)
                    )
                    if target_doc:
                        populated[field] = target_doc
                        
            elif rel.relation_type == RelationType.ONE_TO_MANY:
                # Multiple references
                if isinstance(ref_value, list):
                    populated_list = []
                    for ref_id in ref_value:
                        if isinstance(ref_id, str):
                            target_doc = await self._get_referenced_doc(
                                user_id, rel.to_collection, ref_id,
                                api_key=getattr(self, '_api_key', None)
                            )
                            if target_doc:
                                populated_list.append(target_doc)
                    
                    if populated_list:
                        populated[field] = populated_list
        
        return populated
    
    async def _get_referenced_doc(
        self,
        user_id: str,
        collection: str,
        doc_id: str,
        api_key: str = None
    ) -> Optional[Dict[str, Any]]:
        """Get a referenced document via HTTP API"""
        
        logger.info(f"Getting referenced doc: collection={collection}, id={doc_id}")
        
        if not api_key:
            logger.error("No API key provided")
            return None
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://127.0.0.1:8000/api/storage/read/{doc_id}",
                    headers={"X-API-Key": api_key},
                    params={"collection": collection}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    doc = result.get("data", {})
                    doc["_id"] = doc_id
                    logger.info(f"Found doc: True")
                    return doc
                else:
                    logger.warning(f"Found doc: False (status={response.status_code})")
                    return None
                    
        except Exception as e:
            logger.error(f"Error getting referenced doc: {e}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting referenced doc: {e}")
            logger.info(f"Found doc: False")
            return None
    
    # ========================================================================
    # CASCADE OPERATIONS
    # ========================================================================
    
    async def handle_cascade_delete(
        self,
        user_id: str,
        collection: str,
        doc_id: str
    ) -> List[CascadeResult]:
        """Handle cascade delete operations"""
        
        results = []
        
        # Get relationships where this collection is the target
        relationships = await self.list_relationships(
            user_id=user_id,
            to_collection=collection
        )
        
        for rel in relationships:
            if rel.on_delete == CascadeAction.NONE:
                continue
            
            # Find documents that reference this one
            query = {
                "user_id": user_id,
                rel.from_field: doc_id
            }
            
            referencing_docs = await self.db[rel.from_collection].find(query).to_list(None)
            
            if not referencing_docs:
                continue
            
            affected_count = 0
            
            if rel.on_delete == CascadeAction.SET_NULL:
                # Set reference to null
                result = await self.db[rel.from_collection].update_many(
                    query,
                    {"$set": {rel.from_field: None}}
                )
                affected_count = result.modified_count
            
            elif rel.on_delete == CascadeAction.DELETE:
                # Delete referencing documents
                result = await self.db[rel.from_collection].delete_many(query)
                affected_count = result.deleted_count
            
            elif rel.on_delete == CascadeAction.RESTRICT:
                # Prevent deletion
                if referencing_docs:
                    raise ValueError(
                        f"Cannot delete: {len(referencing_docs)} documents in "
                        f"'{rel.from_collection}' reference this document"
                    )
            
            results.append(CascadeResult(
                action=rel.on_delete,
                affected_collections=[rel.from_collection],
                affected_count=affected_count,
                details={
                    "relationship": rel.name,
                    "field": rel.from_field
                }
            ))
        
        return results
    
    # ========================================================================
    # VALIDATION
    # ========================================================================
    
    async def validate_references(
        self,
        user_id: str,
        collection: str,
        document: Dict[str, Any]
    ) -> BulkReferenceValidation:
        """Validate all references in a document"""
        
        relationships = await self.list_relationships(
            user_id=user_id,
            from_collection=collection
        )
        
        results = []
        
        for rel in relationships:
            field = rel.from_field
            ref_value = document.get(field)
            
            if not ref_value:
                if rel.required:
                    results.append(ReferenceValidationResult(
                        valid=False,
                        field=field,
                        collection=rel.to_collection,
                        reference_id="",
                        exists=False,
                        error_message=f"Required field '{field}' is missing"
                    ))
                continue
            
            # Validate based on type
            if rel.relation_type == RelationType.ONE_TO_ONE:
                exists = await self._reference_exists(
                    user_id, rel.to_collection, ref_value
                )
                results.append(ReferenceValidationResult(
                    valid=exists,
                    field=field,
                    collection=rel.to_collection,
                    reference_id=ref_value,
                    exists=exists,
                    error_message=None if exists else f"Referenced document not found"
                ))
            
            elif rel.relation_type in [RelationType.ONE_TO_MANY, RelationType.MANY_TO_MANY]:
                if isinstance(ref_value, list):
                    for ref_id in ref_value:
                        exists = await self._reference_exists(
                            user_id, rel.to_collection, ref_id
                        )
                        results.append(ReferenceValidationResult(
                            valid=exists,
                            field=field,
                            collection=rel.to_collection,
                            reference_id=ref_id,
                            exists=exists,
                            error_message=None if exists else f"Referenced document not found"
                        ))
        
        valid_count = sum(1 for r in results if r.valid)
        invalid_count = len(results) - valid_count
        
        return BulkReferenceValidation(
            total_checked=len(results),
            valid_count=valid_count,
            invalid_count=invalid_count,
            results=results
        )
    
    async def _reference_exists(
        self,
        user_id: str,
        collection: str,
        doc_id: str
    ) -> bool:
        """Check if referenced document exists via Storage API"""
        
        doc = await self._get_referenced_doc(
            user_id=user_id,
            collection=collection,
            doc_id=doc_id,
            api_key=getattr(self, '_api_key', None)
        )
        
        return doc is not None
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    async def get_relationship_stats(
        self,
        rel_id: str,
        user_id: str
    ) -> RelationshipStats:
        """Get relationship statistics"""
        
        rel = await self.get_relationship(rel_id, user_id)
        
        if not rel:
            raise ValueError("Relationship not found")
        
        # Count total references
        total_refs = await self.db[rel.from_collection].count_documents({
            "user_id": user_id,
            rel.from_field: {"$exists": True, "$ne": None}
        })
        
        # Count broken references (references to non-existent documents)
        broken_refs = 0
        docs = await self.db[rel.from_collection].find({
            "user_id": user_id,
            rel.from_field: {"$exists": True, "$ne": None}
        }).to_list(None)
        
        for doc in docs:
            ref_value = doc.get(rel.from_field)
            
            if isinstance(ref_value, str):
                exists = await self._reference_exists(user_id, rel.to_collection, ref_value)
                if not exists:
                    broken_refs += 1
            
            elif isinstance(ref_value, list):
                for ref_id in ref_value:
                    exists = await self._reference_exists(user_id, rel.to_collection, ref_id)
                    if not exists:
                        broken_refs += 1
        
        return RelationshipStats(
            relationship_id=rel.id,
            relationship_name=rel.name,
            from_collection=rel.from_collection,
            to_collection=rel.to_collection,
            total_references=total_refs,
            broken_references=broken_refs,
            last_validated=datetime.utcnow().isoformat()
        )
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _doc_to_relationship(self, doc: Dict[str, Any]) -> Relationship:
        """Convert document to Relationship"""
        return Relationship(
            id=str(doc["_id"]),
            user_id=doc["user_id"],
            name=doc["name"],
            from_collection=doc["from_collection"],
            to_collection=doc["to_collection"],
            relation_type=RelationType(doc["relation_type"]),
            from_field=doc["from_field"],
            to_field=doc["to_field"],
            on_delete=CascadeAction(doc["on_delete"]),
            on_update=CascadeAction(doc["on_update"]),
            required=doc["required"],
            description=doc.get("description"),
            tags=doc.get("tags", []),
            created_at=doc["created_at"].isoformat(),
            updated_at=doc["updated_at"].isoformat()
        )

    # ========================================================================
    # CASCADE OPERATIONS
    # ========================================================================
    
    async def handle_cascade_delete(
        self,
        user_id: str,
        collection: str,
        document_id: str
    ) -> Dict[str, Any]:
        """
        Handle cascade delete when a document is deleted
        
        Returns:
            Dict with deleted document counts
        """
        
        # Get all relationships where this is the target collection
        relationships = await self.list_relationships(
            user_id=user_id,
            to_collection=collection
        )
        
        deleted_count = 0
        set_null_count = 0
        restricted = []
        
        for rel in relationships:
            if rel.on_delete == CascadeAction.CASCADE:
                # Delete all documents that reference this one
                count = await self._cascade_delete_references(
                    user_id=user_id,
                    from_collection=rel.from_collection,
                    from_field=rel.from_field,
                    target_id=document_id
                )
                deleted_count += count
                
            elif rel.on_delete == CascadeAction.SET_NULL:
                # Set references to null
                count = await self._set_null_references(
                    user_id=user_id,
                    from_collection=rel.from_collection,
                    from_field=rel.from_field,
                    target_id=document_id
                )
                set_null_count += count
                
            elif rel.on_delete == CascadeAction.RESTRICT:
                # Check if any references exist
                has_refs = await self._has_references(
                    user_id=user_id,
                    from_collection=rel.from_collection,
                    from_field=rel.from_field,
                    target_id=document_id
                )
                if has_refs:
                    restricted.append(rel.name)
        
        if restricted:
            raise ValueError(
                f"Cannot delete: referenced by {', '.join(restricted)}"
            )
        
        return {
            "cascade_deleted": deleted_count,
            "set_to_null": set_null_count,
            "restricted": len(restricted)
        }
    
    async def _cascade_delete_references(
        self,
        user_id: str,
        from_collection: str,
        from_field: str,
        target_id: str
    ) -> int:
        """Delete all documents that reference the target"""
        
        import httpx
        api_key = getattr(self, '_api_key', None)
        
        if not api_key:
            logger.warning("No API key for cascade delete")
            return 0
        
        try:
            async with httpx.AsyncClient() as client:
                # Search for documents with reference
                search_response = await client.post(
                    f"http://127.0.0.1:8000/api/search",
                    headers={"X-API-Key": api_key},
                    json={
                        "collection": from_collection,
                        "query": {from_field: target_id}
                    }
                )
                
                if search_response.status_code != 200:
                    return 0
                
                results = search_response.json().get("results", [])
                
                # Delete each document
                deleted = 0
                for doc in results:
                    doc_id = doc.get("id") or doc.get("_id")
                    if doc_id:
                        delete_response = await client.delete(
                            f"http://127.0.0.1:8000/api/storage/delete/{doc_id}",
                            headers={"X-API-Key": api_key},
                            params={"collection": from_collection}
                        )
                        if delete_response.status_code == 200:
                            deleted += 1
                
                return deleted
                
        except Exception as e:
            logger.error(f"Cascade delete error: {e}")
            return 0
    
    async def _set_null_references(
        self,
        user_id: str,
        from_collection: str,
        from_field: str,
        target_id: str
    ) -> int:
        """Set references to null"""
        
        import httpx
        api_key = getattr(self, '_api_key', None)
        
        if not api_key:
            return 0
        
        try:
            async with httpx.AsyncClient() as client:
                # Search for documents
                search_response = await client.post(
                    f"http://127.0.0.1:8000/api/search",
                    headers={"X-API-Key": api_key},
                    json={
                        "collection": from_collection,
                        "query": {from_field: target_id}
                    }
                )
                
                if search_response.status_code != 200:
                    return 0
                
                results = search_response.json().get("results", [])
                
                # Update each document
                updated = 0
                for doc in results:
                    doc_id = doc.get("id") or doc.get("_id")
                    if doc_id:
                        # Remove the reference field
                        doc_data = {k: v for k, v in doc.items() if k != from_field}
                        doc_data[from_field] = None
                        
                        update_response = await client.patch(
                            f"http://127.0.0.1:8000/api/storage/update/{doc_id}",
                            headers={"X-API-Key": api_key},
                            params={"collection": from_collection},
                            json=doc_data
                        )
                        if update_response.status_code == 200:
                            updated += 1
                
                return updated
                
        except Exception as e:
            logger.error(f"Set null error: {e}")
            return 0
    
    async def _has_references(
        self,
        user_id: str,
        from_collection: str,
        from_field: str,
        target_id: str
    ) -> bool:
        """Check if any documents reference the target"""
        
        import httpx
        api_key = getattr(self, '_api_key', None)
        
        if not api_key:
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                search_response = await client.post(
                    f"http://127.0.0.1:8000/api/search",
                    headers={"X-API-Key": api_key},
                    json={
                        "collection": from_collection,
                        "query": {from_field: target_id},
                        "limit": 1
                    }
                )
                
                if search_response.status_code == 200:
                    results = search_response.json().get("results", [])
                    return len(results) > 0
                
                return False
                
        except Exception as e:
            logger.error(f"Check references error: {e}")
            return False
        
    async def populate_document(
        self,
        user_id: str,
        collection: str,
        document: dict,
        populate_fields: List[str],
        depth: int = 1
    ) -> dict:
        """
        Populate references in a document
        
        Args:
            user_id: User ID
            collection: Collection name
            document: Document to populate
            populate_fields: Fields to populate
            depth: Population depth (1-3)
        
        Returns:
            Document with populated references
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if depth <= 0:
            return document
        
        # Get relationships for this collection
        relationships = await self.list_relationships(
            user_id=user_id,
            from_collection=collection
        )
        
        logger.info(f"Found {len(relationships)} relationships for {collection}")
        
        # Process each field
        for field in populate_fields:
            if field not in document:
                logger.warning(f"Field {field} not in document")
                continue
            
            # Find relationship for this field
            rel = None
            for r in relationships:
                if r.from_field == field:
                    rel = r
                    break
            
            if not rel:
                logger.warning(f"No relationship found for field {field}")
                continue
            
            logger.info(f"Populating {field} -> {rel.to_collection}")
            
            field_value = document[field]
            
            # Handle list of references (one-to-many, many-to-many)
            if isinstance(field_value, list):
                populated_values = []
                for ref_id in field_value:
                    if isinstance(ref_id, str):
                        # Fetch from Storage API
                        ref_doc = await self._fetch_from_storage(
                            ref_id, 
                            rel.to_collection
                        )
                        if ref_doc:
                            # Recursively populate if depth > 1
                            if depth > 1:
                                ref_doc = await self.populate_document(
                                    user_id=user_id,
                                    collection=rel.to_collection,
                                    document=ref_doc,
                                    populate_fields=populate_fields,
                                    depth=depth - 1
                                )
                            populated_values.append(ref_doc)  # Add full document
                        else:
                            logger.warning(f"Reference {ref_id} not found")
                
                document[field] = populated_values
            
            # Handle single reference (one-to-one, many-to-one)
            elif isinstance(field_value, str):
                ref_doc = await self._fetch_from_storage(
                    field_value,
                    rel.to_collection
                )
                if ref_doc:
                    # Recursively populate if depth > 1
                    if depth > 1:
                        ref_doc = await self.populate_document(
                            user_id=user_id,
                            collection=rel.to_collection,
                            document=ref_doc,
                            populate_fields=populate_fields,
                            depth=depth - 1
                        )
                    document[field] = ref_doc  # Replace with full document
                else:
                    logger.warning(f"Reference {field_value} not found")
        
        return document
    
    async def _fetch_from_storage(
        self,
        document_id: str,
        collection: str
    ) -> Optional[dict]:
        """
        Fetch document from Storage API
        
        Args:
            document_id: Document ID
            collection: Collection name
        
        Returns:
            Document or None
        """
        import logging
        import httpx
        logger = logging.getLogger(__name__)
        
        try:
            # Use the API key passed from router
            api_key = getattr(self, '_api_key', None)
            if not api_key:
                logger.error("No API key available!")
                return None
            
            logger.info(f"Fetching {document_id} from {collection}")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"http://127.0.0.1:8000/api/storage/read/{document_id}",
                    headers={"X-API-Key": api_key},
                    params={"collection": collection}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    doc = result.get("data", {})
                    doc["_id"] = document_id  # Add _id for compatibility
                    logger.info(f"Document fetched successfully")
                    return doc
                else:
                    logger.error(f"Failed to fetch: {response.status_code}")
                    return None
        
        except Exception as e:
            logger.error(f"Fetch error: {e}")
            return None
