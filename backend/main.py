"""
WoosCloud Storage Backend API
FastAPI + MongoDB + Cloudflare R2
"""
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
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

# Initialize R2 storage
from app.services.r2_storage import R2Storage

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
            "storage": "/api/storage"
        },
        "documentation": "/api/docs",
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