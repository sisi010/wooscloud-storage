from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # MongoDB
    MONGODB_URL: str
    DATABASE_NAME: str = "wooscloud"  # Added!
    
    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_ORIGINS: str = "*"
    
    # Environment
    ENVIRONMENT: str = "development"
    
    # Quota limits (FREE plan)
    FREE_STORAGE_LIMIT: int = 500 * 1024 * 1024  # 500MB
    FREE_API_CALLS_LIMIT: int = 10000  # 10K per month
    
    # Cloudflare R2 Settings
    R2_ENABLED: bool = False
    R2_ACCOUNT_ID: Optional[str] = None
    R2_ACCESS_KEY: Optional[str] = None
    R2_SECRET_KEY: Optional[str] = None
    R2_BUCKET_NAME: str = "wooscloud-storage"
    
    class Config:
        env_file = ".env"

settings = Settings()