"""
WoosCloud Storage - Python Client Library
Simple, powerful, and scalable cloud storage for Python applications
"""

__version__ = "1.0.0"
__author__ = "WoosCloud Team"
__email__ = "support@woos-ai.com"

from .storage import WoosStorage
from .exceptions import (
    WoosCloudError,
    AuthenticationError,
    QuotaExceededError,
    NotFoundError,
    ValidationError
)

__all__ = [
    "WoosStorage",
    "WoosCloudError",
    "AuthenticationError",
    "QuotaExceededError",
    "NotFoundError",
    "ValidationError"
]