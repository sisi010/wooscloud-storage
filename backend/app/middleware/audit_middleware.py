"""
Audit Logging Middleware
Automatically logs all API requests and responses
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from datetime import datetime
import time
import logging

from app.database import get_database
from app.services.audit_service import AuditLogService
from app.models.audit_models import AuditEventType, AuditSeverity, AuditStatus

logger = logging.getLogger(__name__)

class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to automatically log all API requests
    
    Features:
    - Logs all HTTP requests and responses
    - Captures timing information
    - Maps endpoints to event types
    - Automatic severity detection
    - Error tracking
    """
    
    # Endpoint to event type mapping
    EVENT_TYPE_MAP = {
        # Authentication
        "/api/auth/login": AuditEventType.AUTH_LOGIN,
        "/api/auth/logout": AuditEventType.AUTH_LOGOUT,
        
        # Data operations
        "/api/storage/create": AuditEventType.DATA_CREATE,
        "/api/storage/update": AuditEventType.DATA_UPDATE,
        "/api/storage/delete": AuditEventType.DATA_DELETE,
        "/api/storage/list": AuditEventType.DATA_READ,
        "/api/storage/get": AuditEventType.DATA_READ,
        "/api/v2/storage": {
            "POST": AuditEventType.DATA_CREATE,
            "PUT": AuditEventType.DATA_UPDATE,
            "DELETE": AuditEventType.DATA_DELETE,
            "GET": AuditEventType.DATA_READ
        },
        "/api/storage/bulk/create": AuditEventType.DATA_BULK_CREATE,
        "/api/storage/bulk/update": AuditEventType.DATA_BULK_UPDATE,
        "/api/storage/bulk/delete": AuditEventType.DATA_BULK_DELETE,
        "/api/export": AuditEventType.DATA_EXPORT,
        
        # File operations
        "/api/files/upload": AuditEventType.FILE_UPLOAD,
        "/api/files/download": AuditEventType.FILE_DOWNLOAD,
        "/api/files/delete": AuditEventType.FILE_DELETE,
        
        # Search
        "/api/search": AuditEventType.SEARCH_QUERY,
        "/api/search/autocomplete": AuditEventType.SEARCH_AUTOCOMPLETE,
        
        # Backup operations
        "/api/backups": {
            "POST": AuditEventType.BACKUP_CREATE,
            "DELETE": AuditEventType.BACKUP_DELETE
        },
        "/api/backups/restore": AuditEventType.BACKUP_RESTORE,
        
        # Team operations
        "/api/organizations": {
            "POST": AuditEventType.TEAM_ORG_CREATE,
            "PUT": AuditEventType.TEAM_ORG_UPDATE,
            "PATCH": AuditEventType.TEAM_ORG_UPDATE,
            "DELETE": AuditEventType.TEAM_ORG_DELETE
        },
        "/api/teams": AuditEventType.TEAM_TEAM_CREATE,
        "/api/organizations/.*/invitations": AuditEventType.TEAM_MEMBER_INVITE,
        "/api/invitations/accept": AuditEventType.TEAM_MEMBER_JOIN,
        
        # Webhooks
        "/api/webhooks": {
            "POST": AuditEventType.WEBHOOK_CREATE,
            "PUT": AuditEventType.WEBHOOK_UPDATE,
            "DELETE": AuditEventType.WEBHOOK_DELETE
        }
    }
    
    # Paths to exclude from logging (too noisy)
    EXCLUDED_PATHS = [
        "/docs",
        "/openapi.json",
        "/favicon.ico",
        "/health",
        "/api/audit/health"  # Don't log health checks
    ]
    
    async def dispatch(self, request: Request, call_next):
        """Process request and log audit trail"""
        
        # Skip excluded paths
        if any(request.url.path.startswith(path) for path in self.EXCLUDED_PATHS):
            return await call_next(request)
        
        # Start timing
        start_time = time.time()
        
        # Get user info from request state (set by auth middleware)
        user_id = "anonymous"
        api_key_id = None
        
        # Try to get user from auth header
        auth_header = request.headers.get("x-api-key")
        if auth_header:
            try:
                from app.middleware.auth_middleware import get_user_from_api_key
                db = await get_database()
                user = await get_user_from_api_key(auth_header, db)
                if user:
                    user_id = str(user.get("_id"))
                    # Find API key ID
                    api_key_doc = await db.api_keys.find_one({"key": auth_header})
                    if api_key_doc:
                        api_key_id = str(api_key_doc.get("_id"))
            except:
                pass
        
        # Fallback: check request state
        if user_id == "anonymous" and hasattr(request.state, "user"):
            user = request.state.user
            user_id = str(user.get("_id", "anonymous"))
        
        # Process request
        response = await call_next(request)
        
        # Calculate response time
        response_time_ms = int((time.time() - start_time) * 1000)
        
        # Determine event type
        event_type = self._determine_event_type(request)
        
        # Determine severity and status
        severity = self._determine_severity(response.status_code)
        status_enum = self._determine_status(response.status_code)
        
        # Log to audit
        try:
            if user_id:  # Only log if we have user info
                db = await get_database()
                audit_service = AuditLogService(db)
                
                await audit_service.log_event(
                    user_id=user_id,
                    event_type=event_type,
                    status=status_enum,
                    method=request.method,
                    endpoint=request.url.path,
                    response_status=response.status_code,
                    severity=severity,
                    response_time_ms=response_time_ms,
                    ip_address=self._get_client_ip(request),
                    user_agent=request.headers.get("user-agent"),
                    api_key_id=api_key_id,
                    request_params=dict(request.query_params),
                    metadata={
                        "content_type": request.headers.get("content-type"),
                        "referer": request.headers.get("referer")
                    }
                )
        except Exception as e:
            # Don't fail the request if logging fails
            logger.error(f"Failed to log audit event: {e}")
        
        return response
    
    def _determine_event_type(self, request: Request) -> AuditEventType:
        """Determine event type from request"""
        
        path = request.url.path
        method = request.method
        
        # Check exact path match
        if path in self.EVENT_TYPE_MAP:
            mapping = self.EVENT_TYPE_MAP[path]
            
            # If mapping is dict, use method
            if isinstance(mapping, dict):
                return mapping.get(method, AuditEventType.DATA_READ)
            return mapping
        
        # Check pattern match
        for pattern, mapping in self.EVENT_TYPE_MAP.items():
            if "*" in pattern:
                import re
                if re.match(pattern.replace(".*", ".*?"), path):
                    if isinstance(mapping, dict):
                        return mapping.get(method, AuditEventType.DATA_READ)
                    return mapping
        
        # Default based on method
        if method == "POST":
            return AuditEventType.DATA_CREATE
        elif method in ["PUT", "PATCH"]:
            return AuditEventType.DATA_UPDATE
        elif method == "DELETE":
            return AuditEventType.DATA_DELETE
        else:
            return AuditEventType.DATA_READ
    
    def _determine_severity(self, status_code: int) -> AuditSeverity:
        """Determine severity from status code"""
        
        if status_code >= 500:
            return AuditSeverity.ERROR
        elif status_code >= 400:
            if status_code == 401:
                return AuditSeverity.WARNING
            elif status_code == 403:
                return AuditSeverity.WARNING
            elif status_code == 429:
                return AuditSeverity.WARNING
            return AuditSeverity.INFO
        else:
            return AuditSeverity.INFO
    
    def _determine_status(self, status_code: int) -> AuditStatus:
        """Determine audit status from HTTP status code"""
        
        if status_code >= 200 and status_code < 300:
            return AuditStatus.SUCCESS
        elif status_code >= 300 and status_code < 400:
            return AuditStatus.SUCCESS
        else:
            return AuditStatus.FAILURE
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address"""
        
        # Check X-Forwarded-For header (for proxies)
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        
        # Check X-Real-IP header
        real_ip = request.headers.get("x-real-ip")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        if request.client:
            return request.client.host
        
        return "unknown"