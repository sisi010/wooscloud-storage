"""
WoosCloud Storage Backend API
FastAPI + MongoDB + Cloudflare R2
"""
import logging
import asyncio
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s:     %(message)s'
)

logger = logging.getLogger(__name__)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import connect_db, close_db, get_database
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

# Performance optimization imports
from app.utils.performance_optimization import (
    create_performance_indexes,
    warm_cache_on_startup,
    cache_cleanup_task,
    cache
)

# Initialize R2 Storage
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


# ============================================================================
# Lifespan Context Manager (Modern FastAPI approach)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager
    Handles startup and shutdown events
    """
    # ========== STARTUP ==========
    logger.info("🚀 Starting WoosCloud Storage...")
    
    # 1. Connect to database
    await connect_db()
    logger.info("💾 Database connected")
    
    # 2. Start background tasks
    await background_tasks.start()
    logger.info("⚙️  Background tasks started")
    
    # 3. Create performance indexes
    try:
        db = await get_database()
        index_result = await create_performance_indexes(db)
        logger.info(f"📊 Performance indexes: {index_result.get('indexes', [])}")
    except Exception as e:
        logger.warning(f"⚠️  Index creation skipped: {e}")
    
    # 4. Warm up cache
    try:
        warmed = await warm_cache_on_startup(db)
        logger.info(f"🔥 Cache warmed for {warmed} users")
    except Exception as e:
        logger.warning(f"⚠️  Cache warming skipped: {e}")
    
    # 5. Start cache cleanup task
    asyncio.create_task(cache_cleanup_task())
    logger.info("🧹 Cache cleanup task started")
    
    # Log R2 status
    if r2_storage_instance:
        logger.info("💾 Storage: MongoDB + Cloudflare R2")
    else:
        logger.info("💾 Storage: MongoDB only")
    
    logger.info("✅ WoosCloud Storage API ready!")
    
    yield
    
    # ========== SHUTDOWN ==========
    logger.info("👋 Shutting down WoosCloud Storage...")
    
    # 1. Stop background tasks
    await background_tasks.stop()
    logger.info("⚙️  Background tasks stopped")
    
    # 2. Clear cache
    await cache.clear()
    logger.info("🧹 Cache cleared")
    
    # 3. Close database connection
    await close_db()
    logger.info("💾 Database disconnected")
    
    logger.info("✅ WoosCloud Storage API stopped")


# ============================================================================
# Create FastAPI App
# ============================================================================

app = FastAPI(
    title="WoosCloud Storage API",
    description="Simple, powerful, and scalable cloud storage service with R2 integration",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan  # Modern lifespan management
)

# ============================================================================
# Middleware Configuration
# ============================================================================

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


# ============================================================================
# Health Check Endpoints
# ============================================================================

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

@app.get("/api/info")
async def api_info():
    """Get API information"""
    return {
        "name": "WoosCloud Storage API",
        "version": "1.0.0",
        "r2_enabled": settings.R2_ENABLED,
        "storage_provider": "MongoDB + Cloudflare R2" if settings.R2_ENABLED else "MongoDB",
        "features": {
            "ocr": "130+ languages",
            "search": "Atlas Search (Lucene)",
            "storage": "Cloudflare R2",
            "auth": "OAuth2 + 2FA",
            "encryption": "AES-256-GCM"
        },
        "endpoints": {
            "auth": "/api/auth",
            "keys": "/api/keys",
            "storage": "/api/storage",
            "oauth": "/api/oauth",
            "ocr": "/api/ocr",
            "search": "/api/advanced-search"
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
                "ocr": "Unlimited",
                "advanced_search": "Included",
                "price": "$29/month"
            }
        }
    }


# ============================================================================
# Include Routers
# ============================================================================

# Authentication & Security
app.include_router(auth_router.router, prefix="/api/auth", tags=["Authentication"])
app.include_router(api_key_router.router, prefix="/api/keys", tags=["API Keys"])
app.include_router(oauth_router.router, prefix="/api", tags=["OAuth2 Authentication"])
app.include_router(twofa_router.router, prefix="/api", tags=["Two-Factor Authentication"])
app.include_router(encryption_router, prefix="/api", tags=["Encryption"])

# Storage
app.include_router(storage_router.router, prefix="/api/storage", tags=["Storage"])
app.include_router(v2_storage_router.router, prefix="/api/v2", tags=["Storage V2"])
app.include_router(file_router.router, prefix="/api/files", tags=["Files"])
app.include_router(batch_router.router, prefix="/api/batch", tags=["Batch Operations"])

# Search
app.include_router(search_router.router, prefix="/api", tags=["Search"])
app.include_router(unified_search_router.router, prefix="/api", tags=["Unified Search"])
app.include_router(advanced_search_router.router, prefix="/api", tags=["Advanced Search (NEW)"])

# Advanced Storage Features
app.include_router(presigned_urls_router.router, prefix="/api", tags=["Pre-signed URLs"])
app.include_router(multipart_upload_router.router, prefix="/api", tags=["Multipart Upload"])
app.include_router(lifecycle_router.router, prefix="/api", tags=["Lifecycle"])
app.include_router(storage_classes_router.router, prefix="/api", tags=["Storage Classes"])
app.include_router(file_preview_router.router, prefix="/api", tags=["File Preview"])
app.include_router(object_lock_router.router, prefix="/api", tags=["Object Lock"])

# AI & Processing
app.include_router(ocr_router.router, prefix="/api", tags=["OCR (NEW)"])

# CDN & Analytics
app.include_router(cdn_router.router, prefix="/api", tags=["CDN"])
app.include_router(analytics_router.router, prefix="/api", tags=["Analytics"])

# Collaboration
app.include_router(team_router.router, prefix="/api", tags=["Team Collaboration"])
app.include_router(webhook_router.router, prefix="/api", tags=["Webhooks"])
app.include_router(notification_router.router, prefix="/api", tags=["Notifications"])
app.include_router(relationship_router.router, prefix="/api", tags=["Relationships"])

# Operations
app.include_router(backup_router.router, prefix="/api", tags=["Backup & Restore"])
app.include_router(scheduler_router.router, prefix="/api", tags=["Backup Scheduler"])
app.include_router(audit_router.router, prefix="/api", tags=["Audit & Monitoring"])
app.include_router(export_router.router, prefix="/api", tags=["Export"])

# Payment & Billing
app.include_router(payment_router.router, tags=["Payment"])

# Client SDKs
app.include_router(mobile_sdk_router.router, prefix="/api", tags=["Mobile SDK"])
app.include_router(desktop_sync_router.router, prefix="/api", tags=["Desktop Sync"])


# ============================================================================
# Debug: Print All Routes (Development Only)
# ============================================================================

if settings.ENVIRONMENT == "development":
    print("\n" + "="*80)
    print("📋 All Registered Routes:")
    print("="*80)
    for route in app.routes:
        if hasattr(route, 'methods') and hasattr(route, 'path'):
            methods = list(route.methods)[0] if route.methods else "ANY"
            print(f"  {methods:6} {route.path}")
    print("="*80 + "\n")