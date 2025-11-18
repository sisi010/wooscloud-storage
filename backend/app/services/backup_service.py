"""
Backup Service
Handles backup creation, restoration, and management
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import json
import gzip
import io
import logging

from app.models.backup_models import (
    BackupType, BackupStatus, RestoreStatus, ConflictResolution,
    BackupCreateRequest, BackupMetadata, RestoreRequest, RestoreJobMetadata,
    BackupManifest, BackupRecord
)

logger = logging.getLogger(__name__)

class BackupService:
    """
    Backup and Restore Service
    
    Features:
    - Full and incremental backups
    - Compression support
    - Point-in-time recovery
    - Scheduled backups
    - Conflict resolution during restore
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.backups_collection = db.backups
        self.restore_jobs_collection = db.restore_jobs
    
    # ========================================================================
    # CREATE BACKUP
    # ========================================================================
    
    async def create_backup(
        self,
        user_id: str,
        request: BackupCreateRequest
    ) -> BackupMetadata:
        """
        Create a new backup
        
        Args:
            user_id: User ID
            request: Backup request
        
        Returns:
            Backup metadata
        """
        
        backup_id = str(ObjectId())
        
        # Determine collections to backup
        if request.collections:
            collections = request.collections
        else:
            # Get all user's collections
            pipeline = [
                {"$match": {"user_id": user_id}},
                {"$group": {"_id": "$collection"}}
            ]
            result = await self.db.storage_data.aggregate(pipeline).to_list(None)
            collections = [item["_id"] for item in result]
        
        # Create backup metadata
        backup_meta = {
            "_id": backup_id,
            "name": request.name or f"Backup {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
            "user_id": user_id,
            "backup_type": request.backup_type.value,
            "status": BackupStatus.IN_PROGRESS.value,
            "collections": collections,
            "include_files": request.include_files,
            "compressed": request.compress,
            "tags": request.tags or [],
            "created_at": datetime.utcnow(),
            "size_bytes": 0,
            "file_count": 0,
            "record_count": 0
        }
        
        await self.backups_collection.insert_one(backup_meta)
        
        try:
            # Perform backup
            backup_data = await self._perform_backup(
                user_id=user_id,
                backup_id=backup_id,
                collections=collections,
                backup_type=request.backup_type,
                include_files=request.include_files,
                compress=request.compress
            )
            
            # Update metadata with results
            await self.backups_collection.update_one(
                {"_id": backup_id},
                {
                    "$set": {
                        "status": BackupStatus.COMPLETED.value,
                        "completed_at": datetime.utcnow(),
                        "size_bytes": backup_data["size"],
                        "record_count": backup_data["record_count"],
                        "file_count": backup_data["file_count"],
                        "backup_content": backup_data["content"]
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            await self.backups_collection.update_one(
                {"_id": backup_id},
                {
                    "$set": {
                        "status": BackupStatus.FAILED.value,
                        "error_message": str(e),
                        "completed_at": datetime.utcnow()
                    }
                }
            )
            raise
        
        # Get final metadata
        backup_doc = await self.backups_collection.find_one({"_id": backup_id})
        return self._doc_to_metadata(backup_doc)
    
    async def _perform_backup(
        self,
        user_id: str,
        backup_id: str,
        collections: List[str],
        backup_type: BackupType,
        include_files: bool,
        compress: bool
    ) -> Dict[str, Any]:
        """Perform the actual backup operation"""
        
        backup_records = []
        record_count = 0
        file_count = 0
        
        # Backup each collection
        for collection in collections:
            query = {
                "user_id": user_id,
                "collection": collection
            }
            
            # For incremental, only get changed records
            if backup_type == BackupType.INCREMENTAL:
                # Find last backup timestamp
                last_backup = await self.backups_collection.find_one(
                    {
                        "user_id": user_id,
                        "backup_type": BackupType.FULL.value,
                        "status": BackupStatus.COMPLETED.value
                    },
                    sort=[("created_at", -1)]
                )
                
                if last_backup:
                    query["updated_at"] = {"$gte": last_backup["created_at"]}
            
            # Get records
            cursor = self.db.storage_data.find(query)
            async for doc in cursor:
                record = {
                    "collection": doc["collection"],
                    "record_id": str(doc["_id"]),
                    "data": doc.get("data", {}),
                    "metadata": {
                        "size": doc.get("size", 0),
                        "created_at": doc.get("created_at", datetime.utcnow()).isoformat(),
                        "updated_at": doc.get("updated_at", datetime.utcnow()).isoformat(),
                        "version": doc.get("version", 1)
                    },
                    "files": [],
                    "backed_up_at": datetime.utcnow().isoformat()
                }
                
                # Include file references if requested
                if include_files:
                    # Get associated files
                    files = await self.db.files.find({
                        "user_id": user_id,
                        "collection": collection
                    }).to_list(None)
                    record["files"] = [str(f["_id"]) for f in files]
                    file_count += len(files)
                
                backup_records.append(record)
                record_count += 1
        
        # Create manifest
        manifest = {
            "backup_id": backup_id,
            "backup_type": backup_type.value,
            "created_at": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "collections": collections,
            "record_count": record_count,
            "file_count": file_count,
            "compressed": compress
        }
        
        # Combine manifest and records
        backup_content = {
            "manifest": manifest,
            "records": backup_records
        }
        
        # Convert to JSON
        json_data = json.dumps(backup_content, default=str)
        size = len(json_data.encode('utf-8'))
        
        # Compress if requested
        if compress:
            compressed = gzip.compress(json_data.encode('utf-8'))
            size = len(compressed)
            # Store compressed data as base64 for MongoDB
            import base64
            content_to_store = base64.b64encode(compressed).decode('utf-8')
        else:
            content_to_store = json_data
        
        return {
            "content": content_to_store,
            "size": size,
            "record_count": record_count,
            "file_count": file_count
        }
    
    # ========================================================================
    # LIST BACKUPS
    # ========================================================================
    
    async def list_backups(
        self,
        user_id: str,
        limit: int = 10,
        skip: int = 0
    ) -> List[BackupMetadata]:
        """List user's backups"""
        
        cursor = self.backups_collection.find(
            {"user_id": user_id}
        ).sort("created_at", -1).skip(skip).limit(limit)
        
        backups = []
        async for doc in cursor:
            backups.append(self._doc_to_metadata(doc))
        
        return backups
    
    # ========================================================================
    # GET BACKUP
    # ========================================================================
    
    async def get_backup(
        self,
        backup_id: str,
        user_id: str
    ) -> Optional[BackupMetadata]:
        """Get backup by ID"""
        
        doc = await self.backups_collection.find_one({
            "_id": backup_id,
            "user_id": user_id
        })
        
        if not doc:
            return None
        
        return self._doc_to_metadata(doc)
    
    # ========================================================================
    # DELETE BACKUP
    # ========================================================================
    
    async def delete_backup(
        self,
        backup_id: str,
        user_id: str
    ) -> bool:
        """Delete a backup"""
        
        result = await self.backups_collection.delete_one({
            "_id": backup_id,
            "user_id": user_id
        })
        
        return result.deleted_count > 0
    
    # ========================================================================
    # RESTORE
    # ========================================================================
    
    async def restore_backup(
        self,
        user_id: str,
        request: RestoreRequest
    ) -> RestoreJobMetadata:
        """
        Restore from backup
        
        Args:
            user_id: User ID
            request: Restore request
        
        Returns:
            Restore job metadata
        """
        
        # Get backup
        backup = await self.backups_collection.find_one({
            "_id": request.backup_id,
            "user_id": user_id
        })
        
        if not backup:
            raise ValueError(f"Backup {request.backup_id} not found")
        
        if backup["status"] != BackupStatus.COMPLETED.value:
            raise ValueError(f"Backup status is {backup['status']}, cannot restore")
        
        # Create restore job
        job_id = str(ObjectId())
        job_doc = {
            "_id": job_id,
            "backup_id": request.backup_id,
            "user_id": user_id,
            "status": RestoreStatus.IN_PROGRESS.value,
            "collections": request.collections or backup["collections"],
            "conflict_resolution": request.conflict_resolution.value,
            "dry_run": request.dry_run,
            "records_restored": 0,
            "files_restored": 0,
            "conflicts_encountered": 0,
            "conflicts_resolved": {"skip": 0, "overwrite": 0, "rename": 0},
            "created_at": datetime.utcnow()
        }
        
        await self.restore_jobs_collection.insert_one(job_doc)
        
        try:
            # Perform restore
            result = await self._perform_restore(
                user_id=user_id,
                backup=backup,
                request=request
            )
            
            # Update job
            await self.restore_jobs_collection.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": RestoreStatus.COMPLETED.value,
                        "completed_at": datetime.utcnow(),
                        "records_restored": result["records_restored"],
                        "files_restored": result["files_restored"],
                        "conflicts_encountered": result["conflicts_encountered"],
                        "conflicts_resolved": result["conflicts_resolved"]
                    }
                }
            )
            
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            await self.restore_jobs_collection.update_one(
                {"_id": job_id},
                {
                    "$set": {
                        "status": RestoreStatus.FAILED.value,
                        "error_message": str(e),
                        "completed_at": datetime.utcnow()
                    }
                }
            )
            raise
        
        # Get final job metadata
        job_doc = await self.restore_jobs_collection.find_one({"_id": job_id})
        return self._doc_to_restore_job(job_doc)
    
    async def _perform_restore(
        self,
        user_id: str,
        backup: Dict[str, Any],
        request: RestoreRequest
    ) -> Dict[str, Any]:
        """Perform the actual restore operation"""
        
        # Decompress backup content if needed
        content = backup["backup_content"]
        
        if backup["compressed"]:
            import base64
            compressed_data = base64.b64decode(content)
            json_data = gzip.decompress(compressed_data).decode('utf-8')
        else:
            json_data = content
        
        backup_data = json.loads(json_data)
        records = backup_data["records"]
        
        records_restored = 0
        files_restored = 0
        conflicts_encountered = 0
        conflicts_resolved = {"skip": 0, "overwrite": 0, "rename": 0}
        
        # Filter by collections if specified
        if request.collections:
            records = [r for r in records if r["collection"] in request.collections]
        
        # Restore records
        for record in records:
            # Check if record exists
            existing = await self.db.storage_data.find_one({
                "user_id": user_id,
                "collection": record["collection"],
                "_id": ObjectId(record["record_id"])
            })
            
            if existing:
                conflicts_encountered += 1
                
                # Handle conflict
                if request.conflict_resolution == ConflictResolution.SKIP:
                    conflicts_resolved["skip"] += 1
                    continue
                elif request.conflict_resolution == ConflictResolution.OVERWRITE:
                    if not request.dry_run:
                        await self.db.storage_data.replace_one(
                            {"_id": ObjectId(record["record_id"])},
                            {
                                "collection": record["collection"],
                                "user_id": user_id,
                                "data": record["data"],
                                "size": record["metadata"]["size"],
                                "created_at": datetime.fromisoformat(record["metadata"]["created_at"]),
                                "updated_at": datetime.utcnow(),
                                "version": record["metadata"]["version"]
                            }
                        )
                    conflicts_resolved["overwrite"] += 1
                    records_restored += 1
                elif request.conflict_resolution == ConflictResolution.RENAME:
                    # Create new record with different ID
                    if not request.dry_run:
                        await self.db.storage_data.insert_one({
                            "collection": record["collection"],
                            "user_id": user_id,
                            "data": record["data"],
                            "size": record["metadata"]["size"],
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow(),
                            "version": 1
                        })
                    conflicts_resolved["rename"] += 1
                    records_restored += 1
            else:
                # No conflict, insert new record
                if not request.dry_run:
                    await self.db.storage_data.insert_one({
                        "_id": ObjectId(record["record_id"]),
                        "collection": record["collection"],
                        "user_id": user_id,
                        "data": record["data"],
                        "size": record["metadata"]["size"],
                        "created_at": datetime.fromisoformat(record["metadata"]["created_at"]),
                        "updated_at": datetime.utcnow(),
                        "version": record["metadata"]["version"]
                    })
                records_restored += 1
        
        return {
            "records_restored": records_restored,
            "files_restored": files_restored,
            "conflicts_encountered": conflicts_encountered,
            "conflicts_resolved": conflicts_resolved
        }
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _doc_to_metadata(self, doc: Dict[str, Any]) -> BackupMetadata:
        """Convert MongoDB document to BackupMetadata"""
        
        return BackupMetadata(
            id=str(doc["_id"]),
            name=doc["name"],
            user_id=doc["user_id"],
            backup_type=BackupType(doc["backup_type"]),
            status=BackupStatus(doc["status"]),
            collections=doc["collections"],
            include_files=doc["include_files"],
            compressed=doc["compressed"],
            size_bytes=doc.get("size_bytes", 0),
            file_count=doc.get("file_count", 0),
            record_count=doc.get("record_count", 0),
            created_at=doc["created_at"].isoformat(),
            completed_at=doc.get("completed_at").isoformat() if doc.get("completed_at") else None,
            tags=doc.get("tags", []),
            error_message=doc.get("error_message")
        )
    
    def _doc_to_restore_job(self, doc: Dict[str, Any]) -> RestoreJobMetadata:
        """Convert MongoDB document to RestoreJobMetadata"""
        
        return RestoreJobMetadata(
            id=str(doc["_id"]),
            backup_id=doc["backup_id"],
            user_id=doc["user_id"],
            status=RestoreStatus(doc["status"]),
            collections=doc["collections"],
            conflict_resolution=ConflictResolution(doc["conflict_resolution"]),
            dry_run=doc["dry_run"],
            records_restored=doc.get("records_restored", 0),
            files_restored=doc.get("files_restored", 0),
            conflicts_encountered=doc.get("conflicts_encountered", 0),
            conflicts_resolved=doc.get("conflicts_resolved", {}),
            created_at=doc["created_at"].isoformat(),
            completed_at=doc.get("completed_at").isoformat() if doc.get("completed_at") else None,
            error_message=doc.get("error_message")
        )