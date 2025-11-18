"""
OAuth Models
Pydantic models for OAuth2 authentication
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from enum import Enum


class OAuthProvider(str, Enum):
    """Supported OAuth providers"""
    GOOGLE = "google"
    GITHUB = "github"


class OAuthLoginRequest(BaseModel):
    """Request to initiate OAuth login"""
    provider: OAuthProvider = Field(..., description="OAuth provider")
    redirect_url: Optional[str] = Field(None, description="Optional custom redirect URL")
    
    class Config:
        json_schema_extra = {
            "example": {
                "provider": "google",
                "redirect_url": "http://localhost:3000/auth/callback"
            }
        }


class OAuthCallbackRequest(BaseModel):
    """OAuth callback data"""
    code: str = Field(..., description="Authorization code from provider")
    state: Optional[str] = Field(None, description="CSRF protection state")


class OAuthTokenResponse(BaseModel):
    """OAuth token response"""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    refresh_token: Optional[str] = None
    user_id: str
    email: str
    provider: OAuthProvider


class OAuthUserProfile(BaseModel):
    """User profile from OAuth provider"""
    provider: OAuthProvider
    provider_user_id: str
    email: EmailStr
    name: Optional[str] = None
    picture: Optional[str] = None
    verified_email: bool = False
    raw_data: dict = Field(default_factory=dict)


class OAuthConnection(BaseModel):
    """OAuth connection stored in database"""
    id: Optional[str] = None
    user_id: str
    provider: OAuthProvider
    provider_user_id: str
    email: str
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    token_expires_at: Optional[datetime] = None
    scopes: List[str] = Field(default_factory=list)
    connected_at: datetime
    last_used_at: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "507f1f77bcf86cd799439011",
                "provider": "google",
                "provider_user_id": "1234567890",
                "email": "user@gmail.com",
                "scopes": ["openid", "email", "profile"],
                "connected_at": "2025-01-01T00:00:00"
            }
        }


class OAuthLinkRequest(BaseModel):
    """Request to link OAuth account to existing user"""
    provider: OAuthProvider
    code: str


class OAuthUnlinkRequest(BaseModel):
    """Request to unlink OAuth account"""
    provider: OAuthProvider


class OAuthConnectionsResponse(BaseModel):
    """List of user's OAuth connections"""
    connections: List[dict]
    total: int


class OAuthProviderConfig(BaseModel):
    """OAuth provider configuration"""
    provider: OAuthProvider
    client_id: str
    client_secret: str
    authorization_url: str
    token_url: str
    userinfo_url: str
    scopes: List[str]
    redirect_uri: str