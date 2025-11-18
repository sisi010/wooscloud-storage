"""
Webhook management for WoosCloud Storage
"""

from typing import Dict, Any, List, Optional

class WebhookManager:
    """Manages webhooks"""
    
    def __init__(self, client):
        """
        Initialize WebhookManager
        
        Args:
            client: WoosCloudClient instance
        """
        self.client = client
    
    def create(
        self,
        url: str,
        events: List[str],
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new webhook
        
        Args:
            url: Webhook URL to receive events
            events: List of events to subscribe to
                   - "data.created"
                   - "data.updated"
                   - "data.deleted"
                   - "file.uploaded"
            description: Optional description
            
        Returns:
            Webhook information with secret key
            
        Example:
            >>> webhook = storage.webhooks.create(
            ...     url="https://myapp.com/webhook",
            ...     events=["data.created", "file.uploaded"],
            ...     description="Production webhook"
            ... )
            >>> print(f"Webhook ID: {webhook['id']}")
            >>> print(f"Secret: {webhook['secret']}")
        """
        
        data = {
            "url": url,
            "events": events
        }
        
        if description:
            data["description"] = description
        
        return self.client.post("/api/webhooks", json=data)
    
    def list(self) -> List[Dict[str, Any]]:
        """
        List all webhooks
        
        Returns:
            List of webhooks
            
        Example:
            >>> webhooks = storage.webhooks.list()
            >>> for webhook in webhooks:
            ...     print(f"{webhook['id']}: {webhook['url']}")
        """
        
        response = self.client.get("/api/webhooks")
        return response.get("webhooks", [])
    
    def get(self, webhook_id: str) -> Dict[str, Any]:
        """
        Get webhook details by ID
    
        Args:
            webhook_id: Webhook ID
    
        Returns:
            Webhook details dictionary
    
        Example:
            >>> webhook = storage.webhooks.get("webhook_id_here")
            >>> print(webhook["url"])
            >>> print(webhook["events"])
        """
        return self.client.get(f"/api/webhooks/{webhook_id}")
    
    def delete(self, webhook_id: str) -> Dict[str, Any]:
        """
        Delete a webhook
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            Deletion result
            
        Example:
            >>> storage.webhooks.delete("webhook_123")
        """
        
        return self.client.delete(f"/api/webhooks/{webhook_id}")
    
    def test(self, webhook_id: str) -> Dict[str, Any]:
        """
        Test a webhook
        
        Sends a test event to verify the webhook is working
        
        Args:
            webhook_id: Webhook ID
            
        Returns:
            Test result with status and response time
            
        Example:
            >>> result = storage.webhooks.test("webhook_123")
            >>> if result['success']:
            ...     print(f"Webhook works! ({result['response_time_ms']}ms)")
            ... else:
            ...     print(f"Webhook failed: {result['message']}")
        """
        
        return self.client.post(f"/api/webhooks/{webhook_id}/test", json={})
    
    def get_logs(
        self,
        webhook_id: str,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get webhook delivery logs
        
        Args:
            webhook_id: Webhook ID
            limit: Number of logs to retrieve
            
        Returns:
            List of delivery logs
            
        Example:
            >>> logs = storage.webhooks.get_logs("webhook_123", limit=10)
            >>> for log in logs:
            ...     status = "✅" if log['success'] else "❌"
            ...     print(f"{status} {log['event']} - {log['status_code']}")
        """
        
        response = self.client.get(
            f"/api/webhooks/{webhook_id}/logs",
            params={"limit": limit}
        )
        return response.get("logs", [])
    
    def verify_signature(self, payload: str, signature: str, secret: str) -> bool:
        """
        Verify webhook signature
        
        Use this in your webhook handler to verify the request is from WoosCloud
        
        Args:
            payload: Raw request body (string)
            signature: X-Webhook-Signature header value
            secret: Your webhook secret
            
        Returns:
            True if signature is valid
            
        Example:
            >>> from flask import Flask, request
            >>> 
            >>> @app.route('/webhook', methods=['POST'])
            >>> def webhook():
            ...     signature = request.headers.get('X-Webhook-Signature')
            ...     payload = request.get_data(as_text=True)
            ...     
            ...     if not storage.webhooks.verify_signature(payload, signature, SECRET):
            ...         return 'Invalid signature', 401
            ...     
            ...     data = request.json
            ...     print(f"Event: {data['event']}")
            ...     return 'OK', 200
        """
        
        import hmac
        import hashlib
        
        expected_signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        expected_signature = f"sha256={expected_signature}"
        
        return hmac.compare_digest(signature, expected_signature)