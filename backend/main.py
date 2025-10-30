"""
WoosCloud Storage Backend API
FastAPI + MongoDB
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import connect_db, close_db
from app.config import settings

# Import routers
from app.routers import auth_router, storage_router, api_key_router

# Create FastAPI app
app = FastAPI(
    title="WoosCloud Storage API",
    description="Simple, powerful, and scalable cloud storage service",
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
    print("🚀 WoosCloud Storage API started")

@app.on_event("shutdown")
async def shutdown_db_client():
    """Close MongoDB connection on shutdown"""
    await close_db()
    print("👋 WoosCloud Storage API stopped")

# Health check endpoints
@app.get("/")
async def root():
    """API health check"""
    return {
        "service": "WoosCloud Storage API",
        "version": "1.0.0",
        "status": "healthy",
        "docs": "/api/docs"
    }

@app.get("/health")
async def health_check():
    """Detailed health check"""
    return {
        "status": "healthy",
        "database": "connected",
        "environment": settings.ENVIRONMENT
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

# API info endpoint
@app.get("/api/info")
async def api_info():
    """Get API information"""
    return {
        "name": "WoosCloud Storage API",
        "version": "1.0.0",
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