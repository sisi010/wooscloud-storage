"""
Two-Factor Authentication Router
API endpoints for 2FA/TOTP management
"""

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Optional
import logging

from app.models.twofa_models import (
    TwoFactorSetupRequest,
    TwoFactorSetupResponse,
    TwoFactorEnableRequest,
    TwoFactorVerifyRequest,
    TwoFactorDisableRequest,
    TwoFactorStatusResponse,
    TwoFactorBackupCodesResponse
)
from app.services.twofa_service import TwoFactorService
from app.services.auth_service import verify_password
from app.middleware.auth_middleware import verify_api_key
from app.database import get_database

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/2fa", tags=["Two-Factor Authentication"])


# ============================================================================
# 2FA SETUP
# ============================================================================

@router.post("/setup", response_model=TwoFactorSetupResponse)
async def setup_2fa(
    current_user: dict = Depends(verify_api_key)
):
    """
    Setup 2FA for the user
    
    Returns:
    - TOTP secret key
    - QR code (data URL for Google Authenticator)
    - Backup recovery codes
    
    Note: 2FA is not enabled yet. Call /enable after scanning QR code.
    """
    
    try:
        db = await get_database()
        twofa_service = TwoFactorService(db)
        
        # Setup 2FA
        setup_data = await twofa_service.setup_2fa(
            user_id=str(current_user["_id"]),
            email=current_user["email"]
        )
        
        return TwoFactorSetupResponse(
            secret=setup_data["secret"],
            qr_code_url=setup_data["qr_code_url"],
            backup_codes=setup_data["backup_codes"]
        )
        
    except Exception as e:
        logger.error(f"2FA setup failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup 2FA: {str(e)}"
        )


# ============================================================================
# 2FA ENABLE
# ============================================================================

@router.post("/enable")
async def enable_2fa(
    request: TwoFactorEnableRequest,
    current_user: dict = Depends(verify_api_key)
):
    """
    Enable 2FA after verifying the code
    
    After scanning the QR code, verify it works by providing a code.
    """
    
    try:
        db = await get_database()
        twofa_service = TwoFactorService(db)
        
        # Enable 2FA
        await twofa_service.enable_2fa(
            user_id=str(current_user["_id"]),
            code=request.code
        )
        
        return {
            "success": True,
            "message": "2FA enabled successfully",
            "enabled": True
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"2FA enable failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to enable 2FA: {str(e)}"
        )


# ============================================================================
# 2FA VERIFY
# ============================================================================

@router.post("/verify")
async def verify_2fa_code(
    request: TwoFactorVerifyRequest,
    current_user: dict = Depends(verify_api_key)
):
    """
    Verify a 2FA code
    
    Can be used to:
    - Test if 2FA is working
    - Verify before sensitive operations
    """
    
    try:
        db = await get_database()
        twofa_service = TwoFactorService(db)
        
        # Verify code
        is_valid = await twofa_service.verify_2fa(
            user_id=str(current_user["_id"]),
            code=request.code
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code"
            )
        
        return {
            "success": True,
            "message": "2FA code verified",
            "valid": True
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to verify 2FA: {str(e)}"
        )


# ============================================================================
# 2FA DISABLE
# ============================================================================

@router.post("/disable")
async def disable_2fa(
    request: TwoFactorDisableRequest,
    current_user: dict = Depends(verify_api_key)
):
    """
    Disable 2FA
    
    Requires:
    - Valid 2FA code
    - User password
    """
    
    try:
        db = await get_database()
        twofa_service = TwoFactorService(db)
        
        # Verify 2FA code
        is_valid_code = await twofa_service.verify_2fa(
            user_id=str(current_user["_id"]),
            code=request.code
        )
        
        if not is_valid_code:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code"
            )
        
        # Verify password
        if not verify_password(request.password, current_user.get("password_hash", "")):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid password"
            )
        
        # Disable 2FA
        await twofa_service.disable_2fa(str(current_user["_id"]))
        
        return {
            "success": True,
            "message": "2FA disabled successfully",
            "enabled": False
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"2FA disable failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to disable 2FA: {str(e)}"
        )


# ============================================================================
# 2FA STATUS
# ============================================================================

@router.get("/status", response_model=TwoFactorStatusResponse)
async def get_2fa_status(
    current_user: dict = Depends(verify_api_key)
):
    """
    Get 2FA status for the current user
    
    Returns:
    - Whether 2FA is enabled
    - 2FA method (totp)
    - Number of remaining backup codes
    """
    
    try:
        db = await get_database()
        twofa_service = TwoFactorService(db)
        
        status_data = await twofa_service.get_2fa_status(
            user_id=str(current_user["_id"])
        )
        
        return TwoFactorStatusResponse(**status_data)
        
    except Exception as e:
        logger.error(f"Failed to get 2FA status: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get 2FA status: {str(e)}"
        )


# ============================================================================
# BACKUP CODES
# ============================================================================

@router.post("/backup-codes", response_model=TwoFactorBackupCodesResponse)
async def regenerate_backup_codes(
    request: TwoFactorVerifyRequest,
    current_user: dict = Depends(verify_api_key)
):
    """
    Regenerate backup codes
    
    Requires valid 2FA code for security.
    Old backup codes will be invalidated.
    """
    
    try:
        db = await get_database()
        twofa_service = TwoFactorService(db)
        
        # Verify 2FA code
        is_valid = await twofa_service.verify_2fa(
            user_id=str(current_user["_id"]),
            code=request.code
        )
        
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code"
            )
        
        # Regenerate codes
        backup_codes = await twofa_service.regenerate_backup_codes(
            user_id=str(current_user["_id"])
        )
        
        return TwoFactorBackupCodesResponse(backup_codes=backup_codes)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to regenerate backup codes: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate backup codes: {str(e)}"
        )