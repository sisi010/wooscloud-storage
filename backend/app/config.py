"""
Configuration settings
Loads from environment variables
"""
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # MongoDB
    MONGODB_URL: str
    DATABASE_NAME: str = "wooscloud"
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,https://woos-ai.com"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # Storage limits (bytes)
    FREE_STORAGE_LIMIT: int = 500 * 1024 * 1024  # 500MB
    STARTER_STORAGE_LIMIT: int = 5 * 1024 * 1024 * 1024  # 5GB
    PRO_STORAGE_LIMIT: int = 50 * 1024 * 1024 * 1024  # 50GB
    
    # API rate limits
    FREE_API_CALLS_LIMIT: int = 10000  # per month
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Create settings instance
settings = Settings()