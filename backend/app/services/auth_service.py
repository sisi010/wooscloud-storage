"""
Authentication service
Handles password hashing, JWT tokens, etc.
"""
from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional
from app.config import settings
import hashlib

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
    
    Returns:
        True if password matches, False otherwise
    """
    # Truncate password to 72 bytes for bcrypt
    truncated_password = _truncate_password(plain_password)
    return pwd_context.verify(truncated_password, hashed_password)

def get_password_hash(password: str) -> str:
    """
    Hash a password
    
    Args:
        password: Plain text password
    
    Returns:
        Hashed password
    """
    # Truncate password to 72 bytes for bcrypt
    truncated_password = _truncate_password(password)
    return pwd_context.hash(truncated_password)

def _truncate_password(password: str) -> str:
    """
    Truncate password to 72 bytes for bcrypt compatibility
    Uses SHA256 hash if password is too long
    
    Args:
        password: Original password
    
    Returns:
        Truncated or hashed password (max 72 bytes)
    """
    # If password is already short enough, return as-is
    if len(password.encode('utf-8')) <= 72:
        return password
    
    # For longer passwords, use SHA256 hash
    # This ensures security while staying within bcrypt's limit
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create a JWT access token
    
    Args:
        data: Data to encode in token
        expires_delta: Token expiration time
    
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    
    return encoded_jwt

def decode_access_token(token: str) -> Optional[dict]:
    """
    Decode and verify a JWT token
    
    Args:
        token: JWT token string
    
    Returns:
        Decoded payload or None if invalid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        return None

def generate_api_key() -> str:
    """
    Generate a unique API key
    
    Returns:
        API key string starting with 'wai_'
    """
    import secrets
    return f"wai_{secrets.token_urlsafe(32)}"