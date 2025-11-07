"""
Webhook Service
Handles webhook delivery and retry logic
"""

import httpx
import hmac
import hashlib
import json
import secrets
from datetime import datetime
from typing import Dict, Any, List
from bson import ObjectId

class WebhookService:
    """Service for managing and triggering webhooks"""
    
    def __init__(self, db):
        self.db = db
    
    def generate_secret(self) -> str:
        """Generate webhook secret"""
        return f"whsec_{secrets.token_urlsafe(32)}"
    
    def create_signature(self, payload: str, secret: str) -> str:
        """Create HMAC signature for webhook payload"""
        signature = hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return f"sha256={signature}"
    
    async def create_webhook(
        self,
        user_id: str,
        url: str,
        events: List[str],
        description: str = None
    ) -> Dict[str, Any]:
        """Create a new webhook"""
        
        # Validate events
        valid_events = [
            "data.created",
            "data.updated",
            "data.deleted",
            "file.uploaded"
        ]
        
        for event in events:
            if event not in valid_events:
                raise ValueError(f"Invalid event: {event}")
        
        # Generate secret
        secret = self.generate_secret()
        
        # Create webhook document
        webhook = {
            "user_id": user_id,
            "url": url,
            "events": events,
            "secret": secret,
            "is_active": True,
            "description": description,
            "created_at": datetime.utcnow(),
            "last_triggered": None,
            "success_count": 0,
            "failure_count": 0
        }
        
        result = await self.db.webhooks.insert_one(webhook)
        webhook["_id"] = result.inserted_id
        
        return webhook
    
    async def get_webhooks(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all webhooks for a user"""
        cursor = self.db.webhooks.find({"user_id": user_id})
        return await cursor.to_list(length=100)
    
    async def delete_webhook(self, webhook_id: str, user_id: str) -> bool:
        """Delete a webhook"""
        result = await self.db.webhooks.delete_one({
            "_id": ObjectId(webhook_id),
            "user_id": user_id
        })
        return result.deleted_count > 0
    
    async def trigger_event(
        self,
        user_id: str,
        event: str,
        payload: Dict[str, Any]
    ):
        """Trigger webhook for an event"""
        
        # Find all webhooks that listen to this event
        webhooks = await self.db.webhooks.find({
            "user_id": user_id,
            "is_active": True,
            "events": event
        }).to_list(length=100)
        
        # Send to each webhook
        for webhook in webhooks:
            await self._send_webhook(webhook, event, payload)
    
    async def _send_webhook(
        self,
        webhook: Dict[str, Any],
        event: str,
        payload: Dict[str, Any]
    ):
        """Send webhook HTTP request"""
        
        # Prepare payload
        webhook_payload = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            "payload": payload
        }
        
        payload_str = json.dumps(webhook_payload)
        signature = self.create_signature(payload_str, webhook["secret"])
        
        # Send request
        start_time = datetime.utcnow()
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    webhook["url"],
                    json=webhook_payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": signature,
                        "X-Webhook-Event": event
                    }
                )
                
                end_time = datetime.utcnow()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                # Log webhook
                await self._log_webhook(
                    webhook["_id"],
                    event,
                    webhook_payload,
                    response.status_code,
                    response_time,
                    success=response.status_code < 400
                )
                
                # Update webhook stats
                if response.status_code < 400:
                    await self.db.webhooks.update_one(
                        {"_id": webhook["_id"]},
                        {
                            "$set": {"last_triggered": datetime.utcnow()},
                            "$inc": {"success_count": 1}
                        }
                    )
                else:
                    await self.db.webhooks.update_one(
                        {"_id": webhook["_id"]},
                        {"$inc": {"failure_count": 1}}
                    )
                    
        except Exception as e:
            # Log failure
            await self._log_webhook(
                webhook["_id"],
                event,
                webhook_payload,
                0,
                0,
                success=False,
                error=str(e)
            )
            
            # Update failure count
            await self.db.webhooks.update_one(
                {"_id": webhook["_id"]},
                {"$inc": {"failure_count": 1}}
            )
    
    async def _log_webhook(
        self,
        webhook_id: ObjectId,
        event: str,
        payload: Dict[str, Any],
        status_code: int,
        response_time_ms: float,
        success: bool,
        error: str = None
    ):
        """Log webhook delivery"""
        
        log_entry = {
            "webhook_id": webhook_id,
            "event": event,
            "payload": payload,
            "status_code": status_code,
            "response_time_ms": response_time_ms,
            "success": success,
            "error": error,
            "created_at": datetime.utcnow()
        }
        
        await self.db.webhook_logs.insert_one(log_entry)
    
    async def test_webhook(self, webhook_id: str, user_id: str) -> Dict[str, Any]:
        """Test a webhook by sending a test event"""
        
        webhook = await self.db.webhooks.find_one({
            "_id": ObjectId(webhook_id),
            "user_id": user_id
        })
        
        if not webhook:
            raise ValueError("Webhook not found")
        
        # Test payload
        test_payload = {
            "event": "webhook.test",
            "timestamp": datetime.utcnow().isoformat(),
            "payload": {
                "test": True,
                "message": "This is a test webhook"
            }
        }
        
        payload_str = json.dumps(test_payload)
        signature = self.create_signature(payload_str, webhook["secret"])
        
        # Send test request
        start_time = datetime.utcnow()
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    webhook["url"],
                    json=test_payload,
                    headers={
                        "Content-Type": "application/json",
                        "X-Webhook-Signature": signature,
                        "X-Webhook-Event": "webhook.test"
                    }
                )
                
                end_time = datetime.utcnow()
                response_time = (end_time - start_time).total_seconds() * 1000
                
                return {
                    "success": response.status_code < 400,
                    "status_code": response.status_code,
                    "response_time_ms": response_time,
                    "message": f"Webhook test completed with status {response.status_code}"
                }
                
        except Exception as e:
            return {
                "success": False,
                "status_code": 0,
                "response_time_ms": 0,
                "message": f"Webhook test failed: {str(e)}"
            }