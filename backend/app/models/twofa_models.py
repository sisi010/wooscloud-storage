"""
Two-Factor Authentication Models
Pydantic models for 2FA/TOTP authentication
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TwoFactorSetupRequest(BaseModel):
    """Request to setup 2FA"""
    pass  # No input needed, just trigger setup


class TwoFactorSetupResponse(BaseModel):
    """Response with 2FA setup information"""
    secret: str = Field(..., description="TOTP secret key")
    qr_code_url: str = Field(..., description="Data URL for QR code image")
    backup_codes: List[str] = Field(..., description="Backup recovery codes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "secret": "JBSWY3DPEHPK3PXP",
                "qr_code_url": "data:image/png;base64,iVBORw0KGgoAAAANS...",
                "backup_codes": [
                    "1234-5678",
                    "8765-4321",
                    "1111-2222"
                ]
            }
        }


class TwoFactorEnableRequest(BaseModel):
    """Request to enable 2FA"""
    code: str = Field(..., description="6-digit TOTP code", min_length=6, max_length=6)
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "123456"
            }
        }


class TwoFactorVerifyRequest(BaseModel):
    """Request to verify 2FA code"""
    code: str = Field(..., description="6-digit TOTP code or backup code")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "123456"
            }
        }


class TwoFactorDisableRequest(BaseModel):
    """Request to disable 2FA"""
    code: str = Field(..., description="6-digit TOTP code")
    password: str = Field(..., description="User password for verification")
    
    class Config:
        json_schema_extra = {
            "example": {
                "code": "123456",
                "password": "your-password"
            }
        }


class TwoFactorStatusResponse(BaseModel):
    """2FA status response"""
    enabled: bool = Field(..., description="Whether 2FA is enabled")
    method: Optional[str] = Field(None, description="2FA method (totp)")
    backup_codes_remaining: Optional[int] = Field(None, description="Number of unused backup codes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "enabled": True,
                "method": "totp",
                "backup_codes_remaining": 8
            }
        }


class TwoFactorBackupCodesResponse(BaseModel):
    """Response with new backup codes"""
    backup_codes: List[str] = Field(..., description="New backup recovery codes")
    
    class Config:
        json_schema_extra = {
            "example": {
                "backup_codes": [
                    "1234-5678",
                    "8765-4321",
                    "1111-2222",
                    "3333-4444",
                    "5555-6666"
                ]
            }
        }


class LoginWith2FARequest(BaseModel):
    """Login request with 2FA code"""
    email: str = Field(..., description="User email")
    password: str = Field(..., description="User password")
    code: str = Field(..., description="6-digit 2FA code")
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "your-password",
                "code": "123456"
            }
        }


class TwoFactorSettings(BaseModel):
    """2FA settings stored in database"""
    user_id: str
    enabled: bool = False
    secret: Optional[str] = None
    backup_codes: List[str] = Field(default_factory=list)
    created_at: datetime
    enabled_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None