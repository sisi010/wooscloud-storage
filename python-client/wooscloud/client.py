"""
HTTP client for WoosCloud Storage API
"""

import requests
from typing import Dict, Any, Optional
from .exceptions import (
    WoosCloudError,
    AuthenticationError,
    QuotaExceededError,
    NotFoundError,
    ValidationError,
    ConnectionError
)

class WoosCloudClient:
    """Low-level HTTP client for WoosCloud API"""
    
    def __init__(self, api_key: str, base_url: str = "https://wooscloud.up.railway.app"):
        """
        Initialize WoosCloud client
        
        Args:
            api_key: Your WoosCloud API key (starts with 'wai_')
            base_url: API base URL (default: production)
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        })
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request to API
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            params: Query parameters
            json: JSON body
        
        Returns:
            Response data as dictionary
        
        Raises:
            WoosCloudError: On API error
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=json,
                timeout=30
            )
            
            # Handle errors
            if response.status_code >= 400:
                self._handle_error(response)
            
            return response.json()
        
        except requests.exceptions.Timeout:
            raise ConnectionError("Request timeout", status_code=408)
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Connection failed: {str(e)}", status_code=503)
        except requests.exceptions.RequestException as e:
            raise WoosCloudError(f"Request failed: {str(e)}")
    
    def _handle_error(self, response: requests.Response):
        """Handle API error responses"""
        try:
            error_data = response.json()
            message = error_data.get("detail", "Unknown error")
        except:
            message = response.text or f"HTTP {response.status_code}"
        
        if response.status_code == 401:
            raise AuthenticationError(message, status_code=401)
        elif response.status_code == 403:
            raise QuotaExceededError(message, status_code=403)
        elif response.status_code == 404:
            raise NotFoundError(message, status_code=404)
        elif response.status_code == 422:
            raise ValidationError(message, status_code=422)
        else:
            raise WoosCloudError(message, status_code=response.status_code)
    
    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make GET request"""
        return self._request("GET", endpoint, params=params)
    
    def post(self, endpoint: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make POST request"""
        return self._request("POST", endpoint, json=json)
    
    def put(self, endpoint: str, json: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make PUT request"""
        return self._request("PUT", endpoint, json=json)
    
    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make DELETE request"""
        return self._request("DELETE", endpoint)