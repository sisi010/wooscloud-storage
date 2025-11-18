"""
API Version Middleware
Handles API versioning with deprecation warnings and routing
"""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import re
from datetime import datetime

class APIVersionMiddleware(BaseHTTPMiddleware):
    """
    Middleware for API version management
    
    Features:
    - Detects version from URL path (/api/v1/..., /api/v2/...)
    - Adds version headers to response
    - Handles deprecation warnings
    - Logs version usage
    """
    
    # Version configuration
    SUPPORTED_VERSIONS = ["v1", "v2"]
    DEFAULT_VERSION = "v1"
    
    # Deprecation schedule
    DEPRECATED_VERSIONS = {
        "v1": {
            "deprecated_date": "2025-06-01",
            "sunset_date": "2026-01-01",
            "replacement": "v2"
        }
    }
    
    async def dispatch(
        self, 
        request: Request, 
        call_next: Callable
    ) -> Response:
        """
        Process request and add version information
        
        Args:
            request: Incoming request
            call_next: Next middleware/handler
        
        Returns:
            Response with version headers
        """
        
        # Detect API version from URL
        version = self._detect_version(request.url.path)
        
        # Store version in request state for later use
        request.state.api_version = version
        
        # Process request
        response = await call_next(request)
        
        # Add version headers to response
        self._add_version_headers(response, version)
        
        # Add deprecation warning if applicable
        if version in self.DEPRECATED_VERSIONS:
            self._add_deprecation_warning(response, version)
        
        return response
    
    def _detect_version(self, path: str) -> str:
        """
        Detect API version from URL path
        
        Args:
            path: Request path
        
        Returns:
            API version (v1, v2, etc.)
        
        Examples:
            /api/v1/storage/create -> v1
            /api/v2/storage/create -> v2
            /api/storage/create -> v1 (default)
        """
        
        # Pattern: /api/v{number}/...
        pattern = r'/api/(v\d+)/'
        match = re.search(pattern, path)
        
        if match:
            version = match.group(1)
            if version in self.SUPPORTED_VERSIONS:
                return version
        
        # Default version for legacy endpoints without version
        # /api/storage/... -> v1
        if path.startswith('/api/') and not re.search(r'/api/v\d+/', path):
            return self.DEFAULT_VERSION
        
        return self.DEFAULT_VERSION
    
    def _add_version_headers(self, response: Response, version: str):
        """
        Add API version information to response headers
        
        Args:
            response: Response object
            version: API version
        """
        
        response.headers["X-API-Version"] = version
        response.headers["X-API-Supported-Versions"] = ", ".join(self.SUPPORTED_VERSIONS)
        response.headers["X-API-Default-Version"] = self.DEFAULT_VERSION
    
    def _add_deprecation_warning(self, response: Response, version: str):
        """
        Add deprecation warning headers
        
        Args:
            response: Response object
            version: Deprecated API version
        """
        
        if version not in self.DEPRECATED_VERSIONS:
            return
        
        deprecation_info = self.DEPRECATED_VERSIONS[version]
        
        # Add deprecation warning header
        warning_message = (
            f'299 - "API {version} is deprecated. '
            f'Please migrate to {deprecation_info["replacement"]} '
            f'before {deprecation_info["sunset_date"]}"'
        )
        response.headers["Warning"] = warning_message
        
        # Add sunset header (when API will be removed)
        response.headers["Sunset"] = deprecation_info["sunset_date"]
        
        # Add link to migration guide
        response.headers["Link"] = (
            f'<https://docs.wooscloud.com/migration/{version}-to-{deprecation_info["replacement"]}>; '
            f'rel="deprecation"'
        )


class APIVersionInfo:
    """
    API Version Information
    Used to provide version details in responses
    """
    
    @staticmethod
    def get_version_info() -> dict:
        """
        Get comprehensive version information
        
        Returns:
            Dictionary with version details
        """
        
        return {
            "current_version": APIVersionMiddleware.DEFAULT_VERSION,
            "supported_versions": APIVersionMiddleware.SUPPORTED_VERSIONS,
            "deprecated_versions": [
                {
                    "version": version,
                    "deprecated_date": info["deprecated_date"],
                    "sunset_date": info["sunset_date"],
                    "replacement": info["replacement"],
                    "days_until_sunset": APIVersionInfo._calculate_days_until(
                        info["sunset_date"]
                    )
                }
                for version, info in APIVersionMiddleware.DEPRECATED_VERSIONS.items()
            ],
            "latest_version": "v2",
            "documentation_url": "https://docs.wooscloud.com/api-versioning"
        }
    
    @staticmethod
    def _calculate_days_until(date_str: str) -> int:
        """
        Calculate days until given date
        
        Args:
            date_str: Date string (YYYY-MM-DD)
        
        Returns:
            Number of days
        """
        
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d")
            today = datetime.now()
            delta = target_date - today
            return max(0, delta.days)
        except:
            return -1