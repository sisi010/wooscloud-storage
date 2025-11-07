"""
Webhook models
"""

from pydantic import BaseModel, HttpUrl
from typing import List, Optional
from datetime import datetime

class WebhookCreate(BaseModel):
    """Create webhook request"""
    url: str
    events: List[str]
    description: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://myapp.com/webhook",
                "events": ["data.created", "data.updated"],
                "description": "Production webhook"
            }
        }

class WebhookResponse(BaseModel):
    """Webhook response"""
    id: str
    url: str
    events: List[str]
    secret: str
    is_active: bool
    description: Optional[str] = None
    created_at: str
    last_triggered: Optional[str] = None
    success_count: int = 0
    failure_count: int = 0

class WebhookList(BaseModel):
    """List webhooks response"""
    success: bool
    webhooks: List[WebhookResponse]
    total: int

class WebhookTestResponse(BaseModel):
    """Test webhook response"""
    success: bool
    message: str
    status_code: Optional[int] = None
    response_time_ms: Optional[float] = None