"""
Backup Scheduler Service
Automatic backup scheduling and execution
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from croniter import croniter
import asyncio
import logging

from app.models.schedule_models import (
    ScheduleFrequency, ScheduleStatus, BackupJobStatus,
    BackupScheduleCreate, BackupScheduleUpdate, BackupSchedule,
    BackupJob, ScheduleStatistics, ScheduleHealthStatus,
    RetentionPolicyResult, CRON_PRESETS
)
from app.services.backup_service import BackupService
from app.models.backup_models import BackupCreateRequest

logger = logging.getLogger(__name__)

class BackupSchedulerService:
    """
    Backup Scheduler Service
    
    Features:
    - Schedule creation and management
    - Automatic backup execution
    - Retention policy enforcement
    - Job tracking and statistics
    """
    
    # Frequency to cron mapping
    FREQUENCY_CRON_MAP = {
        ScheduleFrequency.HOURLY: "0 * * * *",      # Every hour
        ScheduleFrequency.DAILY: "0 2 * * *",       # 2 AM daily
        ScheduleFrequency.WEEKLY: "0 2 * * 0",      # 2 AM Sunday
        ScheduleFrequency.MONTHLY: "0 2 1 * *"      # 2 AM 1st of month
    }
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.schedules = db.backup_schedules
        self.jobs = db.backup_jobs
    
    # ========================================================================
    # SCHEDULE MANAGEMENT
    # ========================================================================
    
    async def create_schedule(
        self,
        user_id: str,
        request: BackupScheduleCreate
    ) -> BackupSchedule:
        """Create a new backup schedule"""
        
        schedule_id = str(ObjectId())
        
        # Get cron expression
        if request.frequency == ScheduleFrequency.CUSTOM:
            cron_expr = request.cron_expression
        else:
            cron_expr = self.FREQUENCY_CRON_MAP[request.frequency]
        
        # Validate cron expression
        if not self._is_valid_cron(cron_expr):
            raise ValueError(f"Invalid cron expression: {cron_expr}")
        
        # Calculate next run
        next_run = self._calculate_next_run(cron_expr, request.timezone)
        
        schedule_doc = {
            "_id": schedule_id,
            "user_id": user_id,
            "name": request.name,
            "description": request.description,
            "frequency": request.frequency.value,
            "cron_expression": cron_expr,
            "timezone": request.timezone,
            "status": ScheduleStatus.ACTIVE.value,
            "backup_type": request.backup_type,
            "collections": request.collections,
            "include_files": request.include_files,
            "compress": request.compress,
            "retention_days": request.retention_days,
            "max_backups": request.max_backups,
            "last_run_at": None,
            "last_run_status": None,
            "next_run_at": next_run,
            "total_runs": 0,
            "successful_runs": 0,
            "failed_runs": 0,
            "tags": request.tags,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        
        await self.schedules.insert_one(schedule_doc)
        
        return await self.get_schedule(schedule_id, user_id)
    
    async def get_schedule(
        self,
        schedule_id: str,
        user_id: str
    ) -> Optional[BackupSchedule]:
        """Get schedule by ID"""
        
        schedule = await self.schedules.find_one({
            "_id": schedule_id,
            "user_id": user_id
        })
        
        if not schedule:
            return None
        
        return self._doc_to_schedule(schedule)
    
    async def list_schedules(
        self,
        user_id: str,
        status: Optional[ScheduleStatus] = None
    ) -> List[BackupSchedule]:
        """List user's schedules"""
        
        query = {"user_id": user_id}
        
        if status:
            query["status"] = status.value
        
        schedules = await self.schedules.find(query).to_list(None)
        
        return [self._doc_to_schedule(s) for s in schedules]
    
    async def update_schedule(
        self,
        schedule_id: str,
        user_id: str,
        request: BackupScheduleUpdate
    ) -> BackupSchedule:
        """Update schedule"""
        
        schedule = await self.schedules.find_one({
            "_id": schedule_id,
            "user_id": user_id
        })
        
        if not schedule:
            raise ValueError("Schedule not found")
        
        update_doc = {"updated_at": datetime.utcnow()}
        
        # Update fields
        if request.name:
            update_doc["name"] = request.name
        if request.description is not None:
            update_doc["description"] = request.description
        if request.frequency:
            update_doc["frequency"] = request.frequency.value
            # Update cron if frequency changed
            if request.frequency != ScheduleFrequency.CUSTOM:
                update_doc["cron_expression"] = self.FREQUENCY_CRON_MAP[request.frequency]
        if request.cron_expression:
            update_doc["cron_expression"] = request.cron_expression
        if request.timezone:
            update_doc["timezone"] = request.timezone
        if request.backup_type:
            update_doc["backup_type"] = request.backup_type
        if request.collections is not None:
            update_doc["collections"] = request.collections
        if request.include_files is not None:
            update_doc["include_files"] = request.include_files
        if request.compress is not None:
            update_doc["compress"] = request.compress
        if request.retention_days is not None:
            update_doc["retention_days"] = request.retention_days
        if request.max_backups is not None:
            update_doc["max_backups"] = request.max_backups
        if request.status:
            update_doc["status"] = request.status.value
        if request.tags is not None:
            update_doc["tags"] = request.tags
        
        # Recalculate next run if schedule changed
        if any(k in update_doc for k in ["cron_expression", "timezone", "status"]):
            cron_expr = update_doc.get("cron_expression", schedule["cron_expression"])
            timezone = update_doc.get("timezone", schedule["timezone"])
            status = update_doc.get("status", schedule["status"])
            
            if status == ScheduleStatus.ACTIVE.value:
                update_doc["next_run_at"] = self._calculate_next_run(cron_expr, timezone)
            else:
                update_doc["next_run_at"] = None
        
        await self.schedules.update_one(
            {"_id": schedule_id},
            {"$set": update_doc}
        )
        
        return await self.get_schedule(schedule_id, user_id)
    
    async def delete_schedule(
        self,
        schedule_id: str,
        user_id: str
    ) -> bool:
        """Delete schedule"""
        
        result = await self.schedules.delete_one({
            "_id": schedule_id,
            "user_id": user_id
        })
        
        # Also delete associated jobs
        await self.jobs.delete_many({"schedule_id": schedule_id})
        
        return result.deleted_count > 0
    
    # ========================================================================
    # BACKUP EXECUTION
    # ========================================================================
    
    async def execute_schedule(
        self,
        schedule_id: str
    ) -> BackupJob:
        """Execute a schedule (create backup)"""
        
        schedule = await self.schedules.find_one({"_id": schedule_id})
        
        if not schedule:
            raise ValueError("Schedule not found")
        
        if schedule["status"] != ScheduleStatus.ACTIVE.value:
            raise ValueError("Schedule is not active")
        
        # Create job record
        job_id = str(ObjectId())
        job_doc = {
            "_id": job_id,
            "schedule_id": schedule_id,
            "user_id": schedule["user_id"],
            "backup_id": None,
            "status": BackupJobStatus.RUNNING.value,
            "started_at": datetime.utcnow(),
            "completed_at": None,
            "duration_seconds": None,
            "records_backed_up": 0,
            "size_bytes": 0,
            "error_message": None,
            "retry_count": 0,
            "max_retries": 3,
            "metadata": {}
        }
        
        await self.jobs.insert_one(job_doc)
        
        # Execute backup
        try:
            backup_service = BackupService(self.db)
            
            backup_request = BackupCreateRequest(
                name=f"{schedule['name']} - {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}",
                backup_type=schedule["backup_type"],
                collections=schedule.get("collections"),
                include_files=schedule["include_files"],
                compress=schedule["compress"],
                tags=schedule.get("tags", []) + ["scheduled"]
            )
            
            backup = await backup_service.create_backup(
                user_id=schedule["user_id"],
                request=backup_request
            )
            
            # Update job as completed
            completed_at = datetime.utcnow()
            duration = int((completed_at - job_doc["started_at"]).total_seconds())
            
            await self.jobs.update_one(
                {"_id": job_id},
                {"$set": {
                    "backup_id": backup.id,
                    "status": BackupJobStatus.COMPLETED.value,
                    "completed_at": completed_at,
                    "duration_seconds": duration,
                    "records_backed_up": backup.record_count,
                    "size_bytes": backup.size_bytes
                }}
            )
            
            # Update schedule
            next_run = self._calculate_next_run(
                schedule["cron_expression"],
                schedule["timezone"]
            )
            
            await self.schedules.update_one(
                {"_id": schedule_id},
                {
                    "$set": {
                        "last_run_at": completed_at,
                        "last_run_status": BackupJobStatus.COMPLETED.value,
                        "next_run_at": next_run
                    },
                    "$inc": {
                        "total_runs": 1,
                        "successful_runs": 1
                    }
                }
            )
            
            # Apply retention policy
            await self._apply_retention_policy(schedule_id, schedule["user_id"])
            
        except Exception as e:
            logger.error(f"Failed to execute schedule {schedule_id}: {e}")
            
            # Update job as failed
            completed_at = datetime.utcnow()
            duration = int((completed_at - job_doc["started_at"]).total_seconds())
            
            await self.jobs.update_one(
                {"_id": job_id},
                {"$set": {
                    "status": BackupJobStatus.FAILED.value,
                    "completed_at": completed_at,
                    "duration_seconds": duration,
                    "error_message": str(e)
                }}
            )
            
            # Update schedule
            next_run = self._calculate_next_run(
                schedule["cron_expression"],
                schedule["timezone"]
            )
            
            await self.schedules.update_one(
                {"_id": schedule_id},
                {
                    "$set": {
                        "last_run_at": completed_at,
                        "last_run_status": BackupJobStatus.FAILED.value,
                        "next_run_at": next_run
                    },
                    "$inc": {
                        "total_runs": 1,
                        "failed_runs": 1
                    }
                }
            )
        
        # Get updated job
        job = await self.jobs.find_one({"_id": job_id})
        return self._doc_to_job(job)
    
    async def check_and_execute_due_schedules(self):
        """Check and execute all due schedules"""
        
        now = datetime.utcnow()
        
        # Find due schedules
        due_schedules = await self.schedules.find({
            "status": ScheduleStatus.ACTIVE.value,
            "next_run_at": {"$lte": now}
        }).to_list(None)
        
        logger.info(f"Found {len(due_schedules)} due schedules")
        
        for schedule in due_schedules:
            try:
                await self.execute_schedule(schedule["_id"])
            except Exception as e:
                logger.error(f"Failed to execute schedule {schedule['_id']}: {e}")
    
    # ========================================================================
    # RETENTION POLICY
    # ========================================================================
    
    async def _apply_retention_policy(
        self,
        schedule_id: str,
        user_id: str
    ) -> RetentionPolicyResult:
        """Apply retention policy to schedule's backups"""
        
        schedule = await self.schedules.find_one({"_id": schedule_id})
        
        if not schedule:
            return RetentionPolicyResult(
                deleted_backups=[],
                deleted_count=0,
                freed_space_bytes=0,
                reason="schedule_not_found"
            )
        
        # Get all backups from this schedule
        jobs = await self.jobs.find({
            "schedule_id": schedule_id,
            "status": BackupJobStatus.COMPLETED.value,
            "backup_id": {"$ne": None}
        }).sort("completed_at", -1).to_list(None)
        
        deleted_backups = []
        freed_space = 0
        
        # Apply retention by count
        max_backups = schedule.get("max_backups")
        if max_backups and len(jobs) > max_backups:
            # Delete oldest backups
            to_delete = jobs[max_backups:]
            
            for job in to_delete:
                backup_id = job["backup_id"]
                backup = await self.db.backups.find_one({"_id": backup_id})
                
                if backup:
                    freed_space += backup.get("size_bytes", 0)
                    await self.db.backups.delete_one({"_id": backup_id})
                    deleted_backups.append(backup_id)
        
        # Apply retention by age
        retention_days = schedule.get("retention_days")
        if retention_days:
            cutoff_date = datetime.utcnow() - timedelta(days=retention_days)
            
            old_jobs = await self.jobs.find({
                "schedule_id": schedule_id,
                "completed_at": {"$lt": cutoff_date},
                "backup_id": {"$ne": None}
            }).to_list(None)
            
            for job in old_jobs:
                backup_id = job["backup_id"]
                
                if backup_id not in deleted_backups:
                    backup = await self.db.backups.find_one({"_id": backup_id})
                    
                    if backup:
                        freed_space += backup.get("size_bytes", 0)
                        await self.db.backups.delete_one({"_id": backup_id})
                        deleted_backups.append(backup_id)
        
        return RetentionPolicyResult(
            deleted_backups=deleted_backups,
            deleted_count=len(deleted_backups),
            freed_space_bytes=freed_space,
            reason="retention_policy"
        )
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    async def get_schedule_statistics(
        self,
        schedule_id: str,
        user_id: str
    ) -> ScheduleStatistics:
        """Get schedule statistics"""
        
        schedule = await self.schedules.find_one({
            "_id": schedule_id,
            "user_id": user_id
        })
        
        if not schedule:
            raise ValueError("Schedule not found")
        
        # Get jobs
        jobs = await self.jobs.find({"schedule_id": schedule_id}).to_list(None)
        
        total_runs = len(jobs)
        successful = sum(1 for j in jobs if j["status"] == BackupJobStatus.COMPLETED.value)
        failed = sum(1 for j in jobs if j["status"] == BackupJobStatus.FAILED.value)
        skipped = sum(1 for j in jobs if j["status"] == BackupJobStatus.SKIPPED.value)
        
        # Calculate success rate
        success_rate = (successful / total_runs * 100) if total_runs > 0 else 0
        
        # Average duration
        completed_jobs = [j for j in jobs if j.get("duration_seconds")]
        avg_duration = (
            sum(j["duration_seconds"] for j in completed_jobs) / len(completed_jobs)
            if completed_jobs else 0
        )
        
        # Last 7 days
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_jobs = [j for j in jobs if j["started_at"] >= seven_days_ago]
        
        # Total data backed up
        total_data = sum(j.get("size_bytes", 0) for j in jobs)
        
        return ScheduleStatistics(
            schedule_id=schedule_id,
            total_runs=total_runs,
            successful_runs=successful,
            failed_runs=failed,
            skipped_runs=skipped,
            success_rate=round(success_rate, 2),
            average_duration_seconds=round(avg_duration, 2),
            last_7_days_runs=len(recent_jobs),
            total_data_backed_up_bytes=total_data
        )
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _is_valid_cron(self, cron_expr: str) -> bool:
        """Validate cron expression"""
        try:
            croniter(cron_expr)
            return True
        except:
            return False
    
    def _calculate_next_run(self, cron_expr: str, timezone: str) -> datetime:
        """Calculate next run time"""
        now = datetime.utcnow()
        cron = croniter(cron_expr, now)
        return cron.get_next(datetime)
    
    def _doc_to_schedule(self, doc: Dict[str, Any]) -> BackupSchedule:
        """Convert document to BackupSchedule"""
        return BackupSchedule(
            id=str(doc["_id"]),
            user_id=doc["user_id"],
            name=doc["name"],
            description=doc.get("description"),
            frequency=ScheduleFrequency(doc["frequency"]),
            cron_expression=doc.get("cron_expression"),
            timezone=doc["timezone"],
            status=ScheduleStatus(doc["status"]),
            backup_type=doc["backup_type"],
            collections=doc.get("collections"),
            include_files=doc["include_files"],
            compress=doc["compress"],
            retention_days=doc.get("retention_days"),
            max_backups=doc.get("max_backups"),
            last_run_at=doc.get("last_run_at").isoformat() if doc.get("last_run_at") else None,
            last_run_status=BackupJobStatus(doc["last_run_status"]) if doc.get("last_run_status") else None,
            next_run_at=doc.get("next_run_at").isoformat() if doc.get("next_run_at") else None,
            total_runs=doc.get("total_runs", 0),
            successful_runs=doc.get("successful_runs", 0),
            failed_runs=doc.get("failed_runs", 0),
            tags=doc.get("tags", []),
            created_at=doc["created_at"].isoformat(),
            updated_at=doc["updated_at"].isoformat()
        )
    
    def _doc_to_job(self, doc: Dict[str, Any]) -> BackupJob:
        """Convert document to BackupJob"""
        return BackupJob(
            id=str(doc["_id"]),
            schedule_id=doc["schedule_id"],
            user_id=doc["user_id"],
            backup_id=doc.get("backup_id"),
            status=BackupJobStatus(doc["status"]),
            started_at=doc["started_at"].isoformat(),
            completed_at=doc.get("completed_at").isoformat() if doc.get("completed_at") else None,
            duration_seconds=doc.get("duration_seconds"),
            records_backed_up=doc.get("records_backed_up", 0),
            size_bytes=doc.get("size_bytes", 0),
            error_message=doc.get("error_message"),
            retry_count=doc.get("retry_count", 0),
            max_retries=doc.get("max_retries", 3),
            metadata=doc.get("metadata", {})
        )