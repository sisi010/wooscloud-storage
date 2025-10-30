"""
Custom exceptions for WoosCloud Storage
"""

class WoosCloudError(Exception):
    """Base exception for all WoosCloud errors"""
    def __init__(self, message: str, status_code: int = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)

class AuthenticationError(WoosCloudError):
    """Raised when API key is invalid or expired"""
    pass

class QuotaExceededError(WoosCloudError):
    """Raised when storage or API call quota is exceeded"""
    pass

class NotFoundError(WoosCloudError):
    """Raised when requested resource is not found"""
    pass

class ValidationError(WoosCloudError):
    """Raised when input validation fails"""
    pass

class ConnectionError(WoosCloudError):
    """Raised when connection to API fails"""
    pass