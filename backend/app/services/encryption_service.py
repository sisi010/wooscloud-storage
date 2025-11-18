"""
Encryption Service
Handles data encryption at rest using AES-256-GCM
"""

import os
import base64
from typing import Optional, Dict, Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
import logging

logger = logging.getLogger(__name__)


class EncryptionService:
    """
    Service for encrypting and decrypting data at rest
    Uses AES-256-GCM for authenticated encryption
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption service
        
        Args:
            master_key: Master encryption key (from environment)
        """
        self.master_key = master_key or os.getenv(
            "ENCRYPTION_MASTER_KEY",
            "wooscloud-master-key-change-in-production-2025"
        )
        
        if len(self.master_key) < 32:
            logger.warning("Master key is too short! Use at least 32 characters in production")
    
    def _derive_key(self, user_id: str, salt: bytes) -> bytes:
        """
        Derive encryption key from user_id and salt
        
        Args:
            user_id: User ID
            salt: Random salt (16 bytes)
        
        Returns:
            Derived key (32 bytes for AES-256)
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,  # AES-256 requires 32 bytes
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        # Combine master key and user_id as password
        password = f"{self.master_key}:{user_id}".encode('utf-8')
        return kdf.derive(password)
    
    def encrypt(self, plaintext: str, user_id: str) -> str:
        """
        Encrypt plaintext data
        
        Args:
            plaintext: Data to encrypt
            user_id: User ID (for key derivation)
        
        Returns:
            Base64-encoded encrypted data with format:
            base64(salt:nonce:ciphertext:tag)
        """
        try:
            # Generate random salt and nonce
            salt = os.urandom(16)  # 16 bytes
            nonce = os.urandom(12)  # 12 bytes for GCM
            
            # Derive encryption key
            key = self._derive_key(user_id, salt)
            
            # Create cipher
            aesgcm = AESGCM(key)
            
            # Encrypt (includes authentication tag)
            ciphertext = aesgcm.encrypt(
                nonce,
                plaintext.encode('utf-8'),
                None  # No additional authenticated data
            )
            
            # Combine: salt:nonce:ciphertext (ciphertext includes tag)
            encrypted_data = salt + nonce + ciphertext
            
            # Return base64 encoded
            return base64.b64encode(encrypted_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Encryption error: {e}")
            raise ValueError(f"Failed to encrypt data: {str(e)}")
    
    def decrypt(self, encrypted_data: str, user_id: str) -> str:
        """
        Decrypt encrypted data
        
        Args:
            encrypted_data: Base64-encoded encrypted data
            user_id: User ID (for key derivation)
        
        Returns:
            Decrypted plaintext
        """
        try:
            # Decode base64
            data = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Extract components
            salt = data[:16]
            nonce = data[16:28]
            ciphertext = data[28:]  # Includes authentication tag
            
            # Derive decryption key
            key = self._derive_key(user_id, salt)
            
            # Create cipher
            aesgcm = AESGCM(key)
            
            # Decrypt (verifies authentication tag)
            plaintext = aesgcm.decrypt(
                nonce,
                ciphertext,
                None  # No additional authenticated data
            )
            
            return plaintext.decode('utf-8')
            
        except Exception as e:
            logger.error(f"Decryption error: {e}")
            raise ValueError(f"Failed to decrypt data: {str(e)}")
    
    def encrypt_dict(
        self,
        data: Dict[str, Any],
        user_id: str,
        fields_to_encrypt: list[str]
    ) -> Dict[str, Any]:
        """
        Encrypt specific fields in a dictionary
        
        Args:
            data: Dictionary with data
            user_id: User ID
            fields_to_encrypt: List of field names to encrypt
        
        Returns:
            Dictionary with encrypted fields
        """
        result = data.copy()
        
        for field in fields_to_encrypt:
            if field in result and result[field] is not None:
                # Convert to string if not already
                value = str(result[field])
                
                # Encrypt
                encrypted = self.encrypt(value, user_id)
                
                # Store with marker
                result[field] = f"ENC:{encrypted}"
                
                logger.debug(f"Encrypted field: {field}")
        
        return result
    
    def decrypt_dict(
        self,
        data: Dict[str, Any],
        user_id: str,
        fields_to_decrypt: Optional[list[str]] = None
    ) -> Dict[str, Any]:
        """
        Decrypt encrypted fields in a dictionary
        
        Args:
            data: Dictionary with encrypted data
            user_id: User ID
            fields_to_decrypt: List of field names to decrypt (None = auto-detect)
        
        Returns:
            Dictionary with decrypted fields
        """
        result = data.copy()
        
        # Auto-detect encrypted fields if not specified
        if fields_to_decrypt is None:
            fields_to_decrypt = [
                key for key, value in result.items()
                if isinstance(value, str) and value.startswith("ENC:")
            ]
        
        for field in fields_to_decrypt:
            if field in result and isinstance(result[field], str):
                value = result[field]
                
                # Check if encrypted
                if value.startswith("ENC:"):
                    encrypted_data = value[4:]  # Remove "ENC:" prefix
                    
                    try:
                        # Decrypt
                        decrypted = self.decrypt(encrypted_data, user_id)
                        result[field] = decrypted
                        
                        logger.debug(f"Decrypted field: {field}")
                    except Exception as e:
                        logger.error(f"Failed to decrypt field {field}: {e}")
                        # Keep encrypted value if decryption fails
        
        return result
    
    def is_encrypted(self, value: Any) -> bool:
        """
        Check if a value is encrypted
        
        Args:
            value: Value to check
        
        Returns:
            True if encrypted
        """
        return isinstance(value, str) and value.startswith("ENC:")


# Global instance
_encryption_service: Optional[EncryptionService] = None


def get_encryption_service() -> EncryptionService:
    """Get or create encryption service instance"""
    global _encryption_service
    
    if _encryption_service is None:
        _encryption_service = EncryptionService()
    
    return _encryption_service