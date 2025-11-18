"""
WoosCloud Storage Backend API
FastAPI + MongoDB + Cloudflare R2
"""
import logging

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s:     %(message)s'
)

logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import connect_db, close_db
from app.config import settings

# Import routers (separately to avoid circular imports)
from app.routers import auth_router
from app.routers import storage_router  
from app.routers import api_key_router
from app.routers import file_router
from app.routers import batch_router
from app.routers import search_router
from app.routers import webhook_router
from app.middleware.rate_limit_middleware import RateLimitMiddleware
from app.routers import export_router
from app.middleware.version_middleware import APIVersionMiddleware
from app.routers import v2_storage_router
from app.routers import backup_router
from app.routers import team_router
from app.routers import audit_router
from app.middleware.audit_middleware import AuditLoggingMiddleware
from app.services.r2_storage import R2Storage
from app.routers import payment_router
from app.routers import scheduler_router
from app.background_tasks import background_tasks
from app.routers import notification_router
from app.routers import relationship_router
from app.routers.encryption_router import router as encryption_router
from app.routers import oauth_router  
from app.routers import twofa_router
from app.routers import unified_search_router
from app.routers import presigned_urls_router
from app.routers import (
    presigned_urls_router,
    multipart_upload_router,
    lifecycle_router,
    storage_classes_router,
    file_preview_router
)
from app.routers import cdn_router
from app.routers import analytics_router
from app.routers import mobile_sdk_router
from app.routers import desktop_sync_router
from app.routers import object_lock_router
from app.routers import ocr_router
from app.routers import advanced_search_router
   
r2_storage_instance = None
if settings.R2_ENABLED:
    try:
        logger.info("🔧 Initializing R2 storage...")
        r2_storage_instance = R2Storage(
            account_id=settings.R2_ACCOUNT_ID,
            access_key=settings.R2_ACCESS_KEY,
            secret_key=settings.R2_SECRET_KEY,
            bucket_name=settings.R2_BUCKET_NAME
        )
        logger.info("✅ R2 storage initialized successfully")
        logger.info(f"   Bucket: {settings.R2_BUCKET_NAME}")
        logger.info(f"   Account: {settings.R2_ACCOUNT_ID}")
    except Exception as e:
        logger.error(f"❌ Failed to initialize R2: {e}")
        logger.error(f"   R2 will be disabled")
        r2_storage_instance = None
else:
    logger.info("ℹ️  R2 storage disabled (using MongoDB only)")

# Store R2 instance for routers to use
storage_router.r2_storage = r2_storage_instance
file_router.r2_storage = r2_storage_instance
batch_router.r2_storage = r2_storage_instance



# Create FastAPI app
app = FastAPI(
    title="WoosCloud Storage API",
    description="Simple, powerful, and scalable cloud storage service with R2 integration",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuditLoggingMiddleware)
app.add_middleware(APIVersionMiddleware)
# Database connection events
@app.on_event("startup")
async def startup_db_client():
    """Connect to MongoDB on startup"""
    await connect_db()
    logger.info("🚀 WoosCloud Storage API started")
    
    # Log R2 status
    if r2_storage_instance:
        logger.info("💾 Storage: MongoDB + Cloudflare R2")
    else:
        logger.info("💾 Storage: MongoDB only")

@app.on_event("shutdown")
async def shutdown_db_client():
    """Close MongoDB connection on shutdown"""
    await close_db()
    logger.info("👋 WoosCloud Storage API stopped")

# Health check endpoints
@app.get("/")
async def root():
    """API health check"""
    return {
        "service": "WoosCloud Storage API",
        "version": "1.0.0",
        "status": "healthy",
        "r2_enabled": settings.R2_ENABLED,
        "docs": "/api/docs"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "environment": settings.ENVIRONMENT,
        "r2_enabled": settings.R2_ENABLED,
        "storage": "MongoDB + R2" if settings.R2_ENABLED else "MongoDB only"
    }
    
@app.on_event("startup")
async def startup_event():
    """Start background tasks on server startup"""
    await background_tasks.start()
    print("✅ Background tasks started")

@app.on_event("shutdown")
async def shutdown_event():
    """Stop background tasks on server shutdown"""
    await background_tasks.stop()
    print("✅ Background tasks stopped")    

# Include routers
app.include_router(
    auth_router.router,
    prefix="/api/auth",
    tags=["Authentication"]
)

app.include_router(
    api_key_router.router,
    prefix="/api/keys",
    tags=["API Keys"]
)

app.include_router(
    storage_router.router,
    prefix="/api/storage",
    tags=["Storage"]
)

app.include_router(
    file_router.router,
    prefix="/api/files",
    tags=["Files"]
)

app.include_router(
    batch_router.router,
    prefix="/api/batch",
    tags=["Batch Operations"]
)

app.include_router(
    payment_router.router
)

app.include_router(
    search_router.router,
    prefix="/api",
    tags=["Search"]
)

app.include_router(
    webhook_router.router,
    prefix="/api",
    tags=["Webhooks"]
)

app.include_router(
    export_router.router,
    prefix="/api",
    tags=["Export"]
)

app.include_router(
    storage_router.router,
    prefix="/api",
    tags=["Storage V1"]
)

app.include_router(
    v2_storage_router.router,
    prefix="/api/v2",
    tags=["Storage V2"]
)


app.include_router(
    backup_router.router,
    prefix="/api",
    tags=["Backup & Restore"]
)


app.include_router(
    team_router.router,
    prefix="/api",
    tags=["Team Collaboration"]
)

app.include_router(
    audit_router.router,
    prefix="/api",
    tags=["Audit & Monitoring"]
)


app.include_router(
    scheduler_router.router,
    prefix="/api",
    tags=["Backup Scheduler"]
)


app.include_router(
    notification_router.router,
    prefix="/api",
    tags=["Notifications"]
)

app.include_router(
    relationship_router.router,
    prefix="/api",
    tags=["Relationships"]
)

app.include_router(
    encryption_router,
    prefix="/api",
    tags=["Encryption"]
)

app.include_router(
    oauth_router.router,
    prefix="/api",
    tags=["OAuth2 Authentication"]
)

app.include_router(
    twofa_router.router,
    prefix="/api",
    tags=["Two-Factor Authentication"]
)

app.include_router(
    unified_search_router.router,
    prefix="/api",
    tags=["Unified Search"]
)

app.include_router(
    presigned_urls_router.router,
    prefix="/api",
    tags=["Pre-signed URLs"]
)
app.include_router(presigned_urls_router.router, prefix="/api")
app.include_router(multipart_upload_router.router, prefix="/api")
app.include_router(lifecycle_router.router, prefix="/api")
app.include_router(storage_classes_router.router, prefix="/api")
app.include_router(file_preview_router.router, prefix="/api")
app.include_router(cdn_router.router, prefix="/api")
app.include_router(analytics_router.router, prefix="/api")
app.include_router(mobile_sdk_router.router, prefix="/api")
app.include_router(desktop_sync_router.router, prefix="/api")
app.include_router(object_lock_router.router, prefix="/api")
app.include_router(ocr_router.router, prefix="/api")
app.include_router(advanced_search_router.router, prefix="/api")


# DEBUG: Print all routes
print("\n" + "="*80)
print("📋 All Registered Routes:")
print("="*80)
for route in app.routes:
    if hasattr(route, 'methods') and hasattr(route, 'path'):
        methods = list(route.methods)[0] if route.methods else "ANY"
        if '/relationships/' in route.path or '/oauth/' in route.path:
            print(f"  {methods:6} {route.path}")
print("="*80 + "\n")

# API info endpoint
@app.get("/api/info")
async def api_info():
    """Get API information"""
    return {
        "name": "WoosCloud Storage API",
        "version": "1.0.0",
        "r2_enabled": settings.R2_ENABLED,
        "storage_provider": "MongoDB + Cloudflare R2" if settings.R2_ENABLED else "MongoDB",
        "endpoints": {
            "auth": "/api/auth",
            "keys": "/api/keys",
            "storage": "/api/storage",
            "oauth": "/api/oauth"  # NEW
        },
        "documentation": "/api/docs",
        "oauth_providers": {
            "google": "/api/oauth/google/login",
            "github": "/api/oauth/github/login"
        },
        "pricing": {
            "free": {
                "storage": "500 MB",
                "api_calls": "10,000/month",
                "price": "$0"
            },
            "starter": {
                "storage": "5 GB",
                "api_calls": "Unlimited",
                "price": "$9/month"
            },
            "pro": {
                "storage": "50 GB",
                "api_calls": "Unlimited",
                "price": "$29/month"
            }
        }
    }