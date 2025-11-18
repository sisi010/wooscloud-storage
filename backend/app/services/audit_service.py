"""
Audit Log Service
Comprehensive activity tracking and monitoring
"""

from motor.motor_asyncio import AsyncIOMotorDatabase
from bson import ObjectId
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import logging

from app.models.audit_models import (
    AuditEventType, AuditSeverity, AuditStatus,
    AuditLogEntry, AuditLogFilter, AuditStatsResponse,
    SecurityEvent, ActivityTimelineEntry, SystemHealthMetrics
)

logger = logging.getLogger(__name__)

class AuditLogService:
    """
    Audit Log Service
    
    Features:
    - Comprehensive activity logging
    - Advanced filtering and search
    - Statistics and analytics
    - Security event detection
    - Export capabilities
    """
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.audit_logs = db.audit_logs
        self.security_events = db.security_events
    
    # ========================================================================
    # LOG CREATION
    # ========================================================================
    
    async def log_event(
        self,
        user_id: str,
        event_type: AuditEventType,
        status: AuditStatus,
        method: str,
        endpoint: str,
        response_status: int,
        severity: AuditSeverity = AuditSeverity.INFO,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        collection: Optional[str] = None,
        request_params: Optional[Dict[str, Any]] = None,
        request_body: Optional[Dict[str, Any]] = None,
        response_time_ms: Optional[int] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        api_key_id: Optional[str] = None,
        organization_id: Optional[str] = None,
        team_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
        error_code: Optional[str] = None
    ) -> str:
        """Log an audit event"""
        
        log_id = str(ObjectId())
        now = datetime.utcnow()
        
        # Sanitize sensitive data
        sanitized_body = self._sanitize_data(request_body or {})
        sanitized_params = self._sanitize_data(request_params or {})
        
        log_entry = {
            "_id": log_id,
            "user_id": user_id,
            "event_type": event_type.value,
            "severity": severity.value,
            "status": status.value,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "collection": collection,
            "method": method,
            "endpoint": endpoint,
            "request_params": sanitized_params,
            "request_body": sanitized_body,
            "response_status": response_status,
            "response_time_ms": response_time_ms,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "api_key_id": api_key_id,
            "organization_id": organization_id,
            "team_id": team_id,
            "changes": changes or {},
            "metadata": metadata or {},
            "error_message": error_message,
            "error_code": error_code,
            "timestamp": now,
            "created_at": now
        }
        
        await self.audit_logs.insert_one(log_entry)
        
        # Check for security events
        if severity in [AuditSeverity.WARNING, AuditSeverity.ERROR, AuditSeverity.CRITICAL]:
            await self._check_security_event(log_entry)
        
        return log_id
    
    def _sanitize_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove sensitive information from logs"""
        sensitive_keys = [
            "password", "api_key", "secret", "token",
            "authorization", "credit_card", "ssn"
        ]
        
        sanitized = {}
        for key, value in data.items():
            lower_key = key.lower()
            if any(sensitive in lower_key for sensitive in sensitive_keys):
                sanitized[key] = "***REDACTED***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_data(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    # ========================================================================
    # LOG RETRIEVAL
    # ========================================================================
    
    async def get_logs(
        self,
        filters: AuditLogFilter,
        page: int = 1,
        page_size: int = 50,
        sort_by: str = "timestamp",
        sort_order: str = "desc"
    ) -> tuple[List[AuditLogEntry], int]:
        """Get audit logs with filtering"""
        
        # Build query
        query = {}
        
        if filters.user_id:
            query["user_id"] = filters.user_id
        
        if filters.event_type:
            query["event_type"] = filters.event_type.value
        
        if filters.severity:
            query["severity"] = filters.severity.value
        
        if filters.status:
            query["status"] = filters.status.value
        
        if filters.resource_type:
            query["resource_type"] = filters.resource_type
        
        if filters.collection:
            query["collection"] = filters.collection
        
        if filters.organization_id:
            query["organization_id"] = filters.organization_id
        
        if filters.team_id:
            query["team_id"] = filters.team_id
        
        if filters.ip_address:
            query["ip_address"] = filters.ip_address
        
        # Date range
        if filters.start_date or filters.end_date:
            query["timestamp"] = {}
            if filters.start_date:
                query["timestamp"]["$gte"] = datetime.fromisoformat(filters.start_date)
            if filters.end_date:
                query["timestamp"]["$lte"] = datetime.fromisoformat(filters.end_date)
        
        # Text search
        if filters.search:
            query["$or"] = [
                {"endpoint": {"$regex": filters.search, "$options": "i"}},
                {"error_message": {"$regex": filters.search, "$options": "i"}},
                {"metadata": {"$regex": filters.search, "$options": "i"}}
            ]
        
        # Get total count
        total = await self.audit_logs.count_documents(query)
        
        # Get logs
        skip = (page - 1) * page_size
        sort_direction = -1 if sort_order == "desc" else 1
        
        logs = await self.audit_logs.find(query)\
            .sort(sort_by, sort_direction)\
            .skip(skip)\
            .limit(page_size)\
            .to_list(None)
        
        return [self._doc_to_entry(log) for log in logs], total
    
    async def get_log_by_id(self, log_id: str) -> Optional[AuditLogEntry]:
        """Get single audit log by ID"""
        
        log = await self.audit_logs.find_one({"_id": log_id})
        
        if not log:
            return None
        
        return self._doc_to_entry(log)
    
    # ========================================================================
    # STATISTICS
    # ========================================================================
    
    async def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        user_id: Optional[str] = None,
        organization_id: Optional[str] = None
    ) -> AuditStatsResponse:
        """Get audit log statistics"""
        
        # Default to last 30 days
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()
        
        query = {
            "timestamp": {"$gte": start_date, "$lte": end_date}
        }
        
        if user_id:
            query["user_id"] = user_id
        
        if organization_id:
            query["organization_id"] = organization_id
        
        # Total events
        total_events = await self.audit_logs.count_documents(query)
        
        # By event type
        by_event_type = await self.audit_logs.aggregate([
            {"$match": query},
            {"$group": {
                "_id": "$event_type",
                "count": {"$sum": 1},
                "success_count": {
                    "$sum": {"$cond": [{"$eq": ["$status", "success"]}, 1, 0]}
                },
                "failure_count": {
                    "$sum": {"$cond": [{"$eq": ["$status", "failure"]}, 1, 0]}
                }
            }}
        ]).to_list(None)
        
        # By severity
        by_severity = await self.audit_logs.aggregate([
            {"$match": query},
            {"$group": {
                "_id": "$severity",
                "count": {"$sum": 1}
            }}
        ]).to_list(None)
        
        # By status
        by_status = await self.audit_logs.aggregate([
            {"$match": query},
            {"$group": {
                "_id": "$status",
                "count": {"$sum": 1}
            }}
        ]).to_list(None)
        
        # Top users
        top_users = await self.audit_logs.aggregate([
            {"$match": query},
            {"$group": {
                "_id": "$user_id",
                "total_events": {"$sum": 1},
                "last_activity": {"$max": "$timestamp"}
            }},
            {"$sort": {"total_events": -1}},
            {"$limit": 10}
        ]).to_list(None)
        
        # Unique counts
        unique_users = len(await self.audit_logs.distinct("user_id", query))
        unique_ips = len(await self.audit_logs.distinct("ip_address", query))
        
        return AuditStatsResponse(
            total_events=total_events,
            date_range={
                "start": start_date.isoformat(),
                "end": end_date.isoformat()
            },
            by_event_type=[
                {
                    "event_type": item["_id"],
                    "count": item["count"],
                    "success_count": item["success_count"],
                    "failure_count": item["failure_count"]
                }
                for item in by_event_type
            ],
            by_severity=[
                {"severity": item["_id"], "count": item["count"]}
                for item in by_severity
            ],
            by_status={
                item["_id"]: item["count"]
                for item in by_status
            },
            top_users=[
                {
                    "user_id": user["_id"],
                    "total_events": user["total_events"],
                    "last_activity": user["last_activity"].isoformat()
                }
                for user in top_users
            ],
            unique_users=unique_users,
            unique_ips=unique_ips
        )
    
    # ========================================================================
    # SECURITY EVENTS
    # ========================================================================
    
    async def _check_security_event(self, log_entry: Dict[str, Any]):
        """Check for security events"""
        
        event_type = log_entry["event_type"]
        severity = log_entry["severity"]
        
        should_create = False
        description = ""
        
        # Failed auth attempts
        if event_type == AuditEventType.AUTH_FAILED.value:
            should_create = True
            description = "Failed authentication attempt"
        
        # Rate limiting
        elif event_type == AuditEventType.SECURITY_RATE_LIMIT.value:
            should_create = True
            description = "Rate limit exceeded"
        
        # Unauthorized access
        elif event_type == AuditEventType.SECURITY_UNAUTHORIZED.value:
            should_create = True
            description = "Unauthorized access attempt"
        
        # Critical errors
        elif severity == AuditSeverity.CRITICAL.value:
            should_create = True
            description = "Critical system event"
        
        if should_create:
            await self._create_security_event(log_entry, description)
    
    async def _create_security_event(
        self,
        log_entry: Dict[str, Any],
        description: str
    ):
        """Create security event"""
        
        event_id = str(ObjectId())
        
        event_doc = {
            "_id": event_id,
            "severity": log_entry["severity"],
            "event_type": log_entry["event_type"],
            "user_id": log_entry.get("user_id"),
            "ip_address": log_entry.get("ip_address"),
            "description": description,
            "details": {
                "endpoint": log_entry["endpoint"],
                "method": log_entry["method"],
                "status": log_entry["response_status"],
                "error": log_entry.get("error_message")
            },
            "detected_at": datetime.utcnow(),
            "resolved": False
        }
        
        await self.security_events.insert_one(event_doc)
    
    async def get_security_events(
        self,
        resolved: Optional[bool] = None,
        severity: Optional[AuditSeverity] = None
    ) -> List[SecurityEvent]:
        """Get security events"""
        
        query = {}
        
        if resolved is not None:
            query["resolved"] = resolved
        
        if severity:
            query["severity"] = severity.value
        
        events = await self.security_events.find(query)\
            .sort("detected_at", -1)\
            .limit(100)\
            .to_list(None)
        
        return [self._doc_to_security_event(e) for e in events]
    
    # ========================================================================
    # SYSTEM HEALTH
    # ========================================================================
    
    async def get_system_health(self) -> SystemHealthMetrics:
        """Get system health metrics"""
        
        now = datetime.utcnow()
        one_hour_ago = now - timedelta(hours=1)
        
        query = {"timestamp": {"$gte": one_hour_ago}}
        
        # Total requests
        total_requests = await self.audit_logs.count_documents(query)
        
        # Success rate
        success_count = await self.audit_logs.count_documents({
            **query,
            "status": "success"
        })
        success_rate = (success_count / total_requests * 100) if total_requests > 0 else 0
        
        # Average response time
        avg_response = await self.audit_logs.aggregate([
            {"$match": query},
            {"$group": {
                "_id": None,
                "avg": {"$avg": "$response_time_ms"}
            }}
        ]).to_list(None)
        
        avg_response_time = avg_response[0]["avg"] if avg_response else 0
        
        # Error rate
        error_count = await self.audit_logs.count_documents({
            **query,
            "severity": {"$in": ["error", "critical"]}
        })
        error_rate = (error_count / total_requests * 100) if total_requests > 0 else 0
        
        # Active users
        active_users = len(await self.audit_logs.distinct("user_id", query))
        
        # Rate limit hits
        rate_limit_hits = await self.audit_logs.count_documents({
            **query,
            "event_type": AuditEventType.SECURITY_RATE_LIMIT.value
        })
        
        # Security events
        security_events = await self.security_events.count_documents({
            "detected_at": {"$gte": one_hour_ago},
            "resolved": False
        })
        
        return SystemHealthMetrics(
            timestamp=now.isoformat(),
            total_requests_last_hour=total_requests,
            success_rate=round(success_rate, 2),
            average_response_time_ms=round(avg_response_time, 2),
            error_rate=round(error_rate, 2),
            active_users=active_users,
            rate_limit_hits=rate_limit_hits,
            security_events=security_events
        )
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _doc_to_entry(self, doc: Dict[str, Any]) -> AuditLogEntry:
        """Convert document to AuditLogEntry"""
        return AuditLogEntry(
            id=str(doc["_id"]),
            user_id=doc["user_id"],
            event_type=AuditEventType(doc["event_type"]),
            severity=AuditSeverity(doc["severity"]),
            status=AuditStatus(doc["status"]),
            resource_type=doc.get("resource_type"),
            resource_id=doc.get("resource_id"),
            collection=doc.get("collection"),
            method=doc["method"],
            endpoint=doc["endpoint"],
            request_params=doc.get("request_params", {}),
            request_body=doc.get("request_body", {}),
            response_status=doc["response_status"],
            response_time_ms=doc.get("response_time_ms"),
            ip_address=doc.get("ip_address"),
            user_agent=doc.get("user_agent"),
            api_key_id=doc.get("api_key_id"),
            organization_id=doc.get("organization_id"),
            team_id=doc.get("team_id"),
            changes=doc.get("changes", {}),
            metadata=doc.get("metadata", {}),
            error_message=doc.get("error_message"),
            error_code=doc.get("error_code"),
            timestamp=doc["timestamp"].isoformat(),
            created_at=doc["created_at"].isoformat()
        )
    
    def _doc_to_security_event(self, doc: Dict[str, Any]) -> SecurityEvent:
        """Convert document to SecurityEvent"""
        return SecurityEvent(
            id=str(doc["_id"]),
            severity=AuditSeverity(doc["severity"]),
            event_type=AuditEventType(doc["event_type"]),
            user_id=doc.get("user_id"),
            ip_address=doc.get("ip_address"),
            description=doc["description"],
            details=doc.get("details", {}),
            detected_at=doc["detected_at"].isoformat(),
            resolved=doc.get("resolved", False),
            resolved_at=doc.get("resolved_at").isoformat() if doc.get("resolved_at") else None
        )