"""
Lemon Squeezy API Service
Handles communication with Lemon Squeezy payment platform
"""

import requests
from typing import Optional, Dict, Any
from app.config import settings
import os

class LemonSqueezyClient:
    """Client for Lemon Squeezy API"""
    
    def __init__(self):
        self.api_key = os.getenv("LEMON_API_KEY")
        self.store_id = os.getenv("LEMON_STORE_ID")
        self.starter_variant_id = os.getenv("LEMON_STARTER_VARIANT_ID")
        self.pro_variant_id = os.getenv("LEMON_PRO_VARIANT_ID")
        self.webhook_secret = os.getenv("LEMON_WEBHOOK_SECRET")
        
        self.base_url = "https://api.lemonsqueezy.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/vnd.api+json",
            "Content-Type": "application/vnd.api+json"
        }
    
    def create_checkout(
        self,
        variant_id: str,
        user_email: str,
        user_id: str,
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a checkout session
        
        Args:
            variant_id: Product variant ID (STARTER or PRO)
            user_email: Customer email
            user_id: Internal user ID
            success_url: Redirect URL after successful payment
            cancel_url: Redirect URL if payment is cancelled
            
        Returns:
            Checkout session data with URL
        """
        
        endpoint = f"{self.base_url}/checkouts"
        
        # Default URLs
        if not success_url:
            success_url = "https://woos-ai.com/payment-success.html"
        if not cancel_url:
            cancel_url = "https://woos-ai.com/payment-cancel.html"
        
        payload = {
            "data": {
                "type": "checkouts",
                "attributes": {
                    "checkout_data": {
                        "email": user_email,
                        "custom": {
                            "user_id": user_id
                        }
                    }
                },
                "relationships": {
                    "store": {
                        "data": {
                            "type": "stores",
                            "id": self.store_id
                        }
                    },
                    "variant": {
                        "data": {
                            "type": "variants",
                            "id": variant_id
                        }
                    }
                }
            }
        }
        
        try:
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to create checkout: {str(e)}")
    
    def get_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Get subscription details
        
        Args:
            subscription_id: Lemon Squeezy subscription ID
            
        Returns:
            Subscription data
        """
        
        endpoint = f"{self.base_url}/subscriptions/{subscription_id}"
        
        try:
            response = requests.get(
                endpoint,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get subscription: {str(e)}")
    
    def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """
        Cancel a subscription
        
        Args:
            subscription_id: Lemon Squeezy subscription ID
            
        Returns:
            Cancellation result
        """
        
        endpoint = f"{self.base_url}/subscriptions/{subscription_id}"
        
        payload = {
            "data": {
                "type": "subscriptions",
                "id": subscription_id,
                "attributes": {
                    "cancelled": True
                }
            }
        }
        
        try:
            response = requests.patch(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to cancel subscription: {str(e)}")
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify webhook signature from Lemon Squeezy
        
        Args:
            payload: Raw request body
            signature: X-Signature header value
            
        Returns:
            True if signature is valid
        """
        import hmac
        import hashlib
        
        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected_signature, signature)

# Singleton instance
lemon_squeezy = LemonSqueezyClient()