"""
OAuth Service
Handles OAuth2 authentication flows for multiple providers
"""

import httpx
import secrets
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from urllib.parse import urlencode

from app.models.oauth_models import (
    OAuthProvider,
    OAuthUserProfile,
    OAuthProviderConfig,
    OAuthConnection
)

logger = logging.getLogger(__name__)


class OAuthService:
    """
    Service for handling OAuth2 authentication
    
    Supports:
    - Google OAuth2
    - GitHub OAuth2
    """
    
    def __init__(self, db, config: Dict[str, Any]):
        """
        Initialize OAuth service
        
        Args:
            db: MongoDB database instance
            config: OAuth configuration dict
        """
        self.db = db
        self.config = config
        self.providers = self._load_providers()
    
    def _load_providers(self) -> Dict[OAuthProvider, OAuthProviderConfig]:
        """Load OAuth provider configurations"""
        
        providers = {}
        
        # Google OAuth2
        if self.config.get("GOOGLE_CLIENT_ID"):
            providers[OAuthProvider.GOOGLE] = OAuthProviderConfig(
                provider=OAuthProvider.GOOGLE,
                client_id=self.config["GOOGLE_CLIENT_ID"],
                client_secret=self.config["GOOGLE_CLIENT_SECRET"],
                authorization_url="https://accounts.google.com/o/oauth2/v2/auth",
                token_url="https://oauth2.googleapis.com/token",
                userinfo_url="https://www.googleapis.com/oauth2/v2/userinfo",
                scopes=["openid", "email", "profile"],
                redirect_uri=self.config.get("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/oauth/google/callback")
            )
        
        # GitHub OAuth2
        if self.config.get("GITHUB_CLIENT_ID"):
            providers[OAuthProvider.GITHUB] = OAuthProviderConfig(
                provider=OAuthProvider.GITHUB,
                client_id=self.config["GITHUB_CLIENT_ID"],
                client_secret=self.config["GITHUB_CLIENT_SECRET"],
                authorization_url="https://github.com/login/oauth/authorize",
                token_url="https://github.com/login/oauth/access_token",
                userinfo_url="https://api.github.com/user",
                scopes=["user:email"],
                redirect_uri=self.config.get("GITHUB_REDIRECT_URI", "http://localhost:8000/api/oauth/github/callback")
            )
        
        return providers
    
    def get_authorization_url(self, provider: OAuthProvider, state: Optional[str] = None) -> str:
        """
        Get OAuth authorization URL for initiating login
        
        Args:
            provider: OAuth provider (google, github)
            state: CSRF protection state (optional, will be generated if not provided)
        
        Returns:
            Authorization URL to redirect user to
        """
        
        if provider not in self.providers:
            raise ValueError(f"Provider {provider} not configured")
        
        provider_config = self.providers[provider]
        
        # Generate state if not provided (CSRF protection)
        if not state:
            state = secrets.token_urlsafe(32)
        
        # Build authorization parameters
        params = {
            "client_id": provider_config.client_id,
            "redirect_uri": provider_config.redirect_uri,
            "response_type": "code",
            "scope": " ".join(provider_config.scopes),
            "state": state
        }
        
        # GitHub specific parameters
        if provider == OAuthProvider.GITHUB:
            params["allow_signup"] = "true"
        
        # Build URL
        auth_url = f"{provider_config.authorization_url}?{urlencode(params)}"
        
        logger.info(f"Generated {provider} authorization URL")
        
        return auth_url, state
    
    async def exchange_code_for_token(
        self,
        provider: OAuthProvider,
        code: str
    ) -> Dict[str, Any]:
        """
        Exchange authorization code for access token
        
        Args:
            provider: OAuth provider
            code: Authorization code from callback
        
        Returns:
            Token response from provider
        """
        
        if provider not in self.providers:
            raise ValueError(f"Provider {provider} not configured")
        
        provider_config = self.providers[provider]
        
        # Build token request
        data = {
            "client_id": provider_config.client_id,
            "client_secret": provider_config.client_secret,
            "code": code,
            "redirect_uri": provider_config.redirect_uri,
            "grant_type": "authorization_code"
        }
        
        headers = {}
        
        # GitHub requires Accept header
        if provider == OAuthProvider.GITHUB:
            headers["Accept"] = "application/json"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                provider_config.token_url,
                data=data,
                headers=headers,
                timeout=30.0
            )
            
            response.raise_for_status()
            token_data = response.json()
        
        logger.info(f"Successfully exchanged code for {provider} token")
        
        return token_data
    
    async def get_user_profile(
        self,
        provider: OAuthProvider,
        access_token: str
    ) -> OAuthUserProfile:
        """
        Get user profile from OAuth provider
        
        Args:
            provider: OAuth provider
            access_token: Access token
        
        Returns:
            User profile data
        """
        
        if provider not in self.providers:
            raise ValueError(f"Provider {provider} not configured")
        
        provider_config = self.providers[provider]
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                provider_config.userinfo_url,
                headers=headers,
                timeout=30.0
            )
            
            response.raise_for_status()
            user_data = response.json()
            
            # Parse provider-specific response
            if provider == OAuthProvider.GOOGLE:
                profile = OAuthUserProfile(
                    provider=provider,
                    provider_user_id=user_data["id"],
                    email=user_data["email"],
                    name=user_data.get("name"),
                    picture=user_data.get("picture"),
                    verified_email=user_data.get("verified_email", False),
                    raw_data=user_data
                )
            
            elif provider == OAuthProvider.GITHUB:
                # GitHub may need additional email request
                email = user_data.get("email")
                
                if not email:
                    # Request user emails (within same client context)
                    emails_response = await client.get(
                        "https://api.github.com/user/emails",
                        headers=headers,
                        timeout=30.0
                    )
                    emails = emails_response.json()
                    
                    # Get primary email
                    for email_data in emails:
                        if email_data.get("primary"):
                            email = email_data["email"]
                            break
                
                profile = OAuthUserProfile(
                    provider=provider,
                    provider_user_id=str(user_data["id"]),
                    email=email or f"{user_data['login']}@github-no-email.com",
                    name=user_data.get("name") or user_data.get("login"),
                    picture=user_data.get("avatar_url"),
                    verified_email=True,  # GitHub emails are verified
                    raw_data=user_data
                )
            
            else:
                raise ValueError(f"Unsupported provider: {provider}")
        
        logger.info(f"Retrieved {provider} user profile: {profile.email}")
        
        return profile
    
    async def find_or_create_user(self, profile: OAuthUserProfile) -> dict:
        """
        Find existing user or create new one from OAuth profile
        
        Args:
            profile: OAuth user profile
        
        Returns:
            User document
        """
        
        # Try to find user by email
        user = await self.db.users.find_one({"email": profile.email})
        
        if not user:
            # Create new user
            from bson import ObjectId
            
            user_doc = {
                "_id": ObjectId(),
                "email": profile.email,
                "name": profile.name or profile.email.split("@")[0],
                "password_hash": None,  # OAuth users don't have password
                "oauth_provider": profile.provider,
                "oauth_id": profile.provider_user_id,
                "picture": profile.picture,
                "verified": profile.verified_email,
                "plan": "free",
                "storage_used": 0,
                "storage_limit": 500 * 1024 * 1024,  # 500MB
                "api_calls_count": 0,
                "api_calls_limit": 10000,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
            
            await self.db.users.insert_one(user_doc)
            user = user_doc
            
            logger.info(f"Created new user from {profile.provider} OAuth: {profile.email}")
        else:
            logger.info(f"Found existing user: {profile.email}")
        
        return user
    
    async def save_oauth_connection(
        self,
        user_id: str,
        provider: OAuthProvider,
        profile: OAuthUserProfile,
        token_data: Dict[str, Any]
    ) -> OAuthConnection:
        """
        Save OAuth connection to database
        
        Args:
            user_id: User ID
            provider: OAuth provider
            profile: User profile
            token_data: Token response
        
        Returns:
            OAuth connection
        """
        
        # Calculate token expiration
        expires_in = token_data.get("expires_in", 3600)
        token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
        
        connection = {
            "user_id": user_id,
            "provider": provider,
            "provider_user_id": profile.provider_user_id,
            "email": profile.email,
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "token_expires_at": token_expires_at,
            "scopes": token_data.get("scope", "").split() if isinstance(token_data.get("scope"), str) else [],
            "connected_at": datetime.utcnow(),
            "last_used_at": datetime.utcnow()
        }
        
        # Upsert connection (update if exists, insert if not)
        await self.db.oauth_connections.update_one(
            {
                "user_id": user_id,
                "provider": provider
            },
            {"$set": connection},
            upsert=True
        )
        
        logger.info(f"Saved OAuth connection: {user_id} - {provider}")
        
        return OAuthConnection(**connection)
    
    async def get_user_connections(self, user_id: str) -> list:
        """Get all OAuth connections for a user"""
        
        connections = await self.db.oauth_connections.find({
            "user_id": user_id
        }).to_list(None)
        
        # Remove sensitive data
        for conn in connections:
            conn.pop("access_token", None)
            conn.pop("refresh_token", None)
            conn["id"] = str(conn.pop("_id"))
        
        return connections
    
    async def unlink_provider(self, user_id: str, provider: OAuthProvider) -> bool:
        """
        Unlink OAuth provider from user account
        
        Args:
            user_id: User ID
            provider: Provider to unlink
        
        Returns:
            True if unlinked, False if not found
        """
        
        result = await self.db.oauth_connections.delete_one({
            "user_id": user_id,
            "provider": provider
        })
        
        if result.deleted_count > 0:
            logger.info(f"Unlinked {provider} from user {user_id}")
            return True
        
        return False