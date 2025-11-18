"""
Two-Factor Authentication Service
Handles TOTP generation, verification, and backup codes
"""

import pyotp
import qrcode
import io
import base64
import secrets
from typing import Optional, List, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TwoFactorService:
    """
    Service for handling 2FA/TOTP authentication
    
    Features:
    - TOTP secret generation
    - QR code generation for Google Authenticator
    - Code verification
    - Backup codes generation and management
    """
    
    def __init__(self, db):
        """
        Initialize 2FA service
        
        Args:
            db: MongoDB database instance
        """
        self.db = db
    
    def generate_secret(self) -> str:
        """
        Generate a new TOTP secret
        
        Returns:
            Base32-encoded secret key
        """
        return pyotp.random_base32()
    
    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """
        Generate backup recovery codes
        
        Args:
            count: Number of backup codes to generate
        
        Returns:
            List of backup codes in format "XXXX-XXXX"
        """
        codes = []
        for _ in range(count):
            # Generate 8-digit code
            code = secrets.token_hex(4).upper()
            # Format as XXXX-XXXX
            formatted = f"{code[:4]}-{code[4:]}"
            codes.append(formatted)
        
        return codes
    
    def generate_qr_code(self, secret: str, email: str, issuer: str = "WoosCloud Storage") -> str:
        """
        Generate QR code for Google Authenticator
        
        Args:
            secret: TOTP secret
            email: User email
            issuer: Service name
        
        Returns:
            Data URL with base64-encoded QR code image
        """
        # Create TOTP URI
        totp = pyotp.TOTP(secret)
        uri = totp.provisioning_uri(
            name=email,
            issuer_name=issuer
        )
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(uri)
        qr.make(fit=True)
        
        # Create image
        img = qr.make_image(fill_color="black", back_color="white")
        
        # Convert to base64 data URL
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def verify_totp(self, secret: str, code: str) -> bool:
        """
        Verify TOTP code
        
        Args:
            secret: TOTP secret
            code: 6-digit code from authenticator app
        
        Returns:
            True if valid, False otherwise
        """
        try:
            totp = pyotp.TOTP(secret)
            # Allow 1 time window before and after (30 seconds)
            return totp.verify(code, valid_window=1)
        except Exception as e:
            logger.error(f"TOTP verification failed: {e}")
            return False
    
    def verify_backup_code(self, backup_codes: List[str], code: str) -> Tuple[bool, Optional[str]]:
        """
        Verify backup code and return the code to remove if valid
        
        Args:
            backup_codes: List of valid backup codes
            code: Code to verify
        
        Returns:
            Tuple of (is_valid, code_to_remove)
        """
        # Normalize code (remove spaces, dashes, etc.)
        normalized_input = code.replace("-", "").replace(" ", "").upper()
        
        for backup_code in backup_codes:
            normalized_backup = backup_code.replace("-", "").replace(" ", "").upper()
            if normalized_input == normalized_backup:
                return True, backup_code
        
        return False, None
    
    async def setup_2fa(self, user_id: str, email: str) -> dict:
        """
        Setup 2FA for a user (generate secret and QR code)
        
        Args:
            user_id: User ID
            email: User email
        
        Returns:
            Dict with secret, QR code URL, and backup codes
        """
        # Generate secret and backup codes
        secret = self.generate_secret()
        backup_codes = self.generate_backup_codes()
        qr_code_url = self.generate_qr_code(secret, email)
        
        # Store in database (not enabled yet)
        await self.db.twofa_settings.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "user_id": user_id,
                    "enabled": False,
                    "secret": secret,
                    "backup_codes": backup_codes,
                    "created_at": datetime.utcnow(),
                    "enabled_at": None
                }
            },
            upsert=True
        )
        
        logger.info(f"2FA setup initiated for user {user_id}")
        
        return {
            "secret": secret,
            "qr_code_url": qr_code_url,
            "backup_codes": backup_codes
        }
    
    async def enable_2fa(self, user_id: str, code: str) -> bool:
        """
        Enable 2FA after verifying the initial code
        
        Args:
            user_id: User ID
            code: 6-digit verification code
        
        Returns:
            True if enabled successfully
        """
        # Get 2FA settings
        settings = await self.db.twofa_settings.find_one({"user_id": user_id})
        
        if not settings or not settings.get("secret"):
            raise ValueError("2FA not set up. Call setup first.")
        
        # Verify code
        if not self.verify_totp(settings["secret"], code):
            raise ValueError("Invalid verification code")
        
        # Enable 2FA
        await self.db.twofa_settings.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "enabled": True,
                    "enabled_at": datetime.utcnow()
                }
            }
        )
        
        logger.info(f"2FA enabled for user {user_id}")
        
        return True
    
    async def verify_2fa(self, user_id: str, code: str) -> bool:
        """
        Verify 2FA code (TOTP or backup code)
        
        Args:
            user_id: User ID
            code: 6-digit TOTP code or backup code
        
        Returns:
            True if valid
        """
        # Get 2FA settings
        settings = await self.db.twofa_settings.find_one({"user_id": user_id})
        
        if not settings or not settings.get("enabled"):
            return False
        
        # Try TOTP first
        if self.verify_totp(settings["secret"], code):
            # Update last used
            await self.db.twofa_settings.update_one(
                {"user_id": user_id},
                {"$set": {"last_used_at": datetime.utcnow()}}
            )
            return True
        
        # Try backup code
        is_valid, backup_code = self.verify_backup_code(settings.get("backup_codes", []), code)
        
        if is_valid:
            # Remove used backup code
            await self.db.twofa_settings.update_one(
                {"user_id": user_id},
                {
                    "$pull": {"backup_codes": backup_code},
                    "$set": {"last_used_at": datetime.utcnow()}
                }
            )
            logger.info(f"Backup code used for user {user_id}")
            return True
        
        return False
    
    async def disable_2fa(self, user_id: str) -> bool:
        """
        Disable 2FA for a user
        
        Args:
            user_id: User ID
        
        Returns:
            True if disabled successfully
        """
        result = await self.db.twofa_settings.delete_one({"user_id": user_id})
        
        if result.deleted_count > 0:
            logger.info(f"2FA disabled for user {user_id}")
            return True
        
        return False
    
    async def get_2fa_status(self, user_id: str) -> dict:
        """
        Get 2FA status for a user
        
        Args:
            user_id: User ID
        
        Returns:
            Dict with 2FA status
        """
        settings = await self.db.twofa_settings.find_one({"user_id": user_id})
        
        if not settings or not settings.get("enabled"):
            return {
                "enabled": False,
                "method": None,
                "backup_codes_remaining": 0
            }
        
        return {
            "enabled": True,
            "method": "totp",
            "backup_codes_remaining": len(settings.get("backup_codes", []))
        }
    
    async def regenerate_backup_codes(self, user_id: str) -> List[str]:
        """
        Generate new backup codes (replaces old ones)
        
        Args:
            user_id: User ID
        
        Returns:
            New backup codes
        """
        # Generate new codes
        backup_codes = self.generate_backup_codes()
        
        # Update in database
        await self.db.twofa_settings.update_one(
            {"user_id": user_id},
            {"$set": {"backup_codes": backup_codes}}
        )
        
        logger.info(f"Regenerated backup codes for user {user_id}")
        
        return backup_codes