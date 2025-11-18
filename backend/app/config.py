"""
Configuration Settings
Environment variables and application settings
"""

from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # MongoDB
    MONGODB_URL: str
    DATABASE_NAME: str = "wooscloud"
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_ORIGINS: str = "*"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # Quota limits (FREE plan)
    FREE_STORAGE_LIMIT: int = 1024 * 1024 * 1024  # 1GB
    FREE_API_CALLS_LIMIT: int = 10000  # 10K per month
    
    # Quota limits (STARTER plan)
    STARTER_STORAGE_LIMIT: int = 5 * 1024 * 1024 * 1024  # 5GB
    
    # Quota limits (PRO plan)
    PRO_STORAGE_LIMIT: int = 50 * 1024 * 1024 * 1024  # 50GB
    
    # Cloudflare R2 Settings
    R2_ENABLED: bool = False
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY: Optional[str] = None
    R2_SECRET_KEY: Optional[str] = None
    R2_BUCKET_NAME: str = "wooscloud-storage"
    
    # OAuth2 Settings - Google
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/api/oauth/google/callback"
    
    # OAuth2 Settings - GitHub
    GITHUB_CLIENT_ID: Optional[str] = None
    GITHUB_CLIENT_SECRET: Optional[str] = None
    GITHUB_REDIRECT_URI: str = "http://localhost:8000/api/oauth/github/callback"
    
    base_url: str = "http://127.0.0.1:8000"
    
    # ========================================
    # Compatibility Properties
    # ========================================
    @property
    def jwt_secret(self) -> str:
        """JWT secret alias for compatibility with pre-signed URLs"""
        return self.SECRET_KEY
    
    @property
    def jwt_algorithm(self) -> str:
        """JWT algorithm alias for compatibility"""
        return self.ALGORITHM
    
    class Config:
        env_file = ".env"

settings = Settings()