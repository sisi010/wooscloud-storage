"""
OAuth Router
API endpoints for OAuth2 authentication
"""

from fastapi import APIRouter, HTTPException, Depends, status, Query, Request
from fastapi.responses import RedirectResponse
from typing import Optional
import logging

from app.models.oauth_models import (
    OAuthProvider,
    OAuthLoginRequest,
    OAuthCallbackRequest,
    OAuthTokenResponse,
    OAuthConnectionsResponse,
    OAuthUnlinkRequest
)
from app.services.oauth_service import OAuthService
from app.services.auth_service import create_access_token
from app.middleware.auth_middleware import verify_api_key
from app.database import get_database
from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/oauth")


def get_oauth_service(db) -> OAuthService:
    """Get OAuth service instance"""
    
    config = {
        "GOOGLE_CLIENT_ID": getattr(settings, "GOOGLE_CLIENT_ID", None),
        "GOOGLE_CLIENT_SECRET": getattr(settings, "GOOGLE_CLIENT_SECRET", None),
        "GOOGLE_REDIRECT_URI": getattr(settings, "GOOGLE_REDIRECT_URI", "http://localhost:8000/api/oauth/google/callback"),
        "GITHUB_CLIENT_ID": getattr(settings, "GITHUB_CLIENT_ID", None),
        "GITHUB_CLIENT_SECRET": getattr(settings, "GITHUB_CLIENT_SECRET", None),
        "GITHUB_REDIRECT_URI": getattr(settings, "GITHUB_REDIRECT_URI", "http://localhost:8000/api/oauth/github/callback"),
    }
    
    return OAuthService(db, config)


# ============================================================================
# GOOGLE OAUTH
# ============================================================================

@router.get("/google/login")
async def google_login(
    redirect_url: Optional[str] = Query(None, description="Custom redirect URL after login")
):
    """
    Initiate Google OAuth2 login
    
    Redirects user to Google login page
    """
    
    try:
        db = await get_database()
        oauth_service = get_oauth_service(db)
        
        # Generate authorization URL with state for CSRF protection
        auth_url, state = oauth_service.get_authorization_url(OAuthProvider.GOOGLE)
        
        logger.info(f"Redirecting to Google OAuth: {auth_url}")
        
        return RedirectResponse(url=auth_url)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Google OAuth not configured: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Google login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate Google login: {str(e)}"
        )


@router.get("/google/callback")
async def google_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: Optional[str] = Query(None, description="CSRF protection state")
):
    """
    Google OAuth2 callback
    
    Exchanges code for token and creates/logs in user
    """
    
    try:
        db = await get_database()
        oauth_service = get_oauth_service(db)
        
        # Exchange code for token
        token_data = await oauth_service.exchange_code_for_token(
            OAuthProvider.GOOGLE,
            code
        )
        
        # Get user profile
        profile = await oauth_service.get_user_profile(
            OAuthProvider.GOOGLE,
            token_data["access_token"]
        )
        
        # Find or create user
        user = await oauth_service.find_or_create_user(profile)
        
        # Save OAuth connection
        await oauth_service.save_oauth_connection(
            user_id=str(user["_id"]),
            provider=OAuthProvider.GOOGLE,
            profile=profile,
            token_data=token_data
        )
        
        # Generate JWT token for API access
        access_token = create_access_token(data={"sub": str(user["_id"])})
        
        # In production, redirect to frontend with token
        # For now, return JSON response
        return {
            "success": True,
            "message": "Successfully logged in with Google",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user["_id"]),
                "email": user["email"],
                "name": user.get("name"),
                "provider": "google"
            }
        }
        
    except Exception as e:
        logger.error(f"Google callback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete Google login: {str(e)}"
        )


# ============================================================================
# GITHUB OAUTH
# ============================================================================

@router.get("/github/login")
async def github_login(
    redirect_url: Optional[str] = Query(None, description="Custom redirect URL after login")
):
    """
    Initiate GitHub OAuth2 login
    
    Redirects user to GitHub login page
    """
    
    try:
        db = await get_database()
        oauth_service = get_oauth_service(db)
        
        # Generate authorization URL
        auth_url, state = oauth_service.get_authorization_url(OAuthProvider.GITHUB)
        
        logger.info(f"Redirecting to GitHub OAuth: {auth_url}")
        
        return RedirectResponse(url=auth_url)
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"GitHub OAuth not configured: {str(e)}"
        )
    except Exception as e:
        logger.error(f"GitHub login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate GitHub login: {str(e)}"
        )


@router.get("/github/callback")
async def github_callback(
    code: str = Query(..., description="Authorization code from GitHub"),
    state: Optional[str] = Query(None, description="CSRF protection state")
):
    """
    GitHub OAuth2 callback
    
    Exchanges code for token and creates/logs in user
    """
    
    try:
        db = await get_database()
        oauth_service = get_oauth_service(db)
        
        # Exchange code for token
        token_data = await oauth_service.exchange_code_for_token(
            OAuthProvider.GITHUB,
            code
        )
        
        # Get user profile
        profile = await oauth_service.get_user_profile(
            OAuthProvider.GITHUB,
            token_data["access_token"]
        )
        
        # Find or create user
        user = await oauth_service.find_or_create_user(profile)
        
        # Save OAuth connection
        await oauth_service.save_oauth_connection(
            user_id=str(user["_id"]),
            provider=OAuthProvider.GITHUB,
            profile=profile,
            token_data=token_data
        )
        
        # Generate JWT token
        access_token = create_access_token(data={"sub": str(user["_id"])})
        
        return {
            "success": True,
            "message": "Successfully logged in with GitHub",
            "access_token": access_token,
            "token_type": "bearer",
            "user": {
                "id": str(user["_id"]),
                "email": user["email"],
                "name": user.get("name"),
                "provider": "github"
            }
        }
        
    except Exception as e:
        logger.error(f"GitHub callback failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to complete GitHub login: {str(e)}"
        )


# ============================================================================
# OAUTH CONNECTIONS MANAGEMENT
# ============================================================================

@router.get("/connections", response_model=OAuthConnectionsResponse)
async def get_oauth_connections(
    current_user: dict = Depends(verify_api_key)
):
    """
    Get user's OAuth connections
    
    Returns list of connected OAuth providers
    """
    
    try:
        db = await get_database()
        oauth_service = get_oauth_service(db)
        
        connections = await oauth_service.get_user_connections(
            user_id=str(current_user["_id"])
        )
        
        return OAuthConnectionsResponse(
            connections=connections,
            total=len(connections)
        )
        
    except Exception as e:
        logger.error(f"Failed to get OAuth connections: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get OAuth connections: {str(e)}"
        )


@router.delete("/connections/{provider}")
async def unlink_oauth_provider(
    provider: OAuthProvider,
    current_user: dict = Depends(verify_api_key)
):
    """
    Unlink OAuth provider from account
    
    Removes OAuth connection but keeps the account
    """
    
    try:
        db = await get_database()
        oauth_service = get_oauth_service(db)
        
        # Check if user has password (can't unlink if OAuth is only auth method)
        user = await db.users.find_one({"_id": current_user["_id"]})
        
        if not user.get("password_hash"):
            # Count other OAuth connections
            other_connections = await db.oauth_connections.count_documents({
                "user_id": str(current_user["_id"]),
                "provider": {"$ne": provider}
            })
            
            if other_connections == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot unlink last authentication method. Set a password first."
                )
        
        success = await oauth_service.unlink_provider(
            user_id=str(current_user["_id"]),
            provider=provider
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No {provider} connection found"
            )
        
        return {
            "success": True,
            "message": f"Successfully unlinked {provider}",
            "provider": provider
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to unlink OAuth provider: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unlink provider: {str(e)}"
        )


# ============================================================================
# OAUTH PROVIDERS INFO
# ============================================================================

@router.get("/providers")
async def get_oauth_providers():
    """
    Get list of configured OAuth providers
    
    Returns which OAuth providers are available
    """
    
    db = await get_database()
    oauth_service = get_oauth_service(db)
    
    providers = []
    
    for provider in oauth_service.providers.keys():
        # Convert enum to string value
        provider_str = provider.value if hasattr(provider, 'value') else str(provider)
        
        providers.append({
            "provider": provider_str,
            "name": provider_str.title(),
            "login_url": f"/api/oauth/{provider_str}/login",
            "available": True
        })
    
    return {
        "providers": providers,
        "total": len(providers)
    }