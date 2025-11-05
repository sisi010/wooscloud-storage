"""
Payment Router - Lemon Squeezy Integration
Handles subscription payments and upgrades
"""

from fastapi import APIRouter, HTTPException, Depends, Request
from typing import Dict, Any
from pydantic import BaseModel
from app.middleware.auth_middleware import verify_api_key
from app.database import get_database
from app.services.lemonsqueezy import lemon_squeezy
from bson import ObjectId
import os

router = APIRouter(prefix="/api/payment", tags=["payment"])


class CheckoutRequest(BaseModel):
    """Checkout request model"""
    plan: str  # "starter" or "pro"


class CheckoutResponse(BaseModel):
    """Checkout response model"""
    checkout_url: str
    plan: str
    price: str


@router.post("/create-checkout", response_model=CheckoutResponse)
async def create_checkout(
    request: CheckoutRequest,
    current_user: Dict[str, Any] = Depends(verify_api_key)
):
    """
    Create a payment checkout session
    
    Args:
        request: Checkout request with plan selection
        current_user: Authenticated user
        
    Returns:
        Checkout URL for payment
    """
    
    # Validate plan
    plan = request.plan.lower()
    if plan not in ["starter", "pro"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid plan. Must be 'starter' or 'pro'"
        )
    
    # Get variant ID based on plan
    if plan == "starter":
        variant_id = os.getenv("LEMON_STARTER_VARIANT_ID")
        price = "$9/month"
    else:  # pro
        variant_id = os.getenv("LEMON_PRO_VARIANT_ID")
        price = "$29/month"
    
    if not variant_id:
        raise HTTPException(
            status_code=500,
            detail="Payment system configuration error"
        )
    
    # Create checkout session
    try:
        checkout_data = lemon_squeezy.create_checkout(
            variant_id=variant_id,
            user_email=current_user["email"],
            user_id=str(current_user["_id"])
        )
        
        # Extract checkout URL
        checkout_url = checkout_data["data"]["attributes"]["url"]
        
        return CheckoutResponse(
            checkout_url=checkout_url,
            plan=plan,
            price=price
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create checkout: {str(e)}"
        )


@router.get("/subscription")
async def get_subscription(
    current_user: Dict[str, Any] = Depends(verify_api_key)
):
    """
    Get current user's subscription details
    
    Returns:
        Current plan and subscription info
    """
    
    return {
        "plan": current_user.get("plan", "free"),
        "storage_limit_mb": current_user.get("storage_limit", 0) / 1024 / 1024,
        "storage_used_mb": current_user.get("storage_used", 0) / 1024 / 1024,
        "api_calls_count": current_user.get("api_calls_count", 0),
        "api_calls_limit": current_user.get("api_calls_limit", 10000)
    }


@router.post("/webhook")
async def webhook(request: Request):
    """
    Webhook endpoint for Lemon Squeezy events
    
    Handles:
    - subscription_created: New subscription
    - subscription_updated: Subscription changes
    - subscription_cancelled: Cancellation
    - subscription_payment_success: Successful payment
    """
    
    # Get raw body for signature verification
    body = await request.body()
    signature = request.headers.get("X-Signature", "")
    
    # Verify webhook signature
    if not lemon_squeezy.verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse webhook data
    import json
    data = json.loads(body)
    
    event_name = data.get("meta", {}).get("event_name")
    attributes = data.get("data", {}).get("attributes", {})
    
    # Extract user ID from custom data
    custom_data = attributes.get("custom_data", {})
    user_id = custom_data.get("user_id")
    
    if not user_id:
        return {"status": "ignored", "reason": "no user_id"}
    
    # Get database
    db = await get_database()
    
    # Handle different events
    if event_name == "subscription_created":
        # New subscription
        variant_id = str(attributes.get("variant_id"))
        
        # Determine plan
        starter_id = os.getenv("LEMON_STARTER_VARIANT_ID")
        pro_id = os.getenv("LEMON_PRO_VARIANT_ID")
        
        if variant_id == starter_id:
            plan = "starter"
            storage_limit = 5 * 1024 * 1024 * 1024  # 5GB
        elif variant_id == pro_id:
            plan = "pro"
            storage_limit = 50 * 1024 * 1024 * 1024  # 50GB
        else:
            return {"status": "ignored", "reason": "unknown variant"}
        
        # Update user plan
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "plan": plan,
                    "storage_limit": storage_limit,
                    "api_calls_limit": -1,  # Unlimited
                    "lemon_subscription_id": attributes.get("id")
                }
            }
        )
        
        return {"status": "success", "event": "subscription_created", "plan": plan}
    
    elif event_name == "subscription_cancelled":
        # Subscription cancelled - downgrade to free
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "plan": "free",
                    "storage_limit": 1024 * 1024 * 1024,  # 1GB
                    "api_calls_limit": 10000,
                    "lemon_subscription_id": None
                }
            }
        )
        
        return {"status": "success", "event": "subscription_cancelled"}
    
    elif event_name == "subscription_payment_success":
        # Payment successful - extend subscription
        return {"status": "success", "event": "payment_success"}

    elif event_name == "subscription_updated":
        # Subscription updated - handle plan upgrade
        variant_id = str(attributes.get("variant_id"))
    
        # Determine plan
        starter_id = os.getenv("LEMON_STARTER_VARIANT_ID")
        pro_id = os.getenv("LEMON_PRO_VARIANT_ID")
    
        if variant_id == starter_id:
            plan = "starter"
            storage_limit = 5 * 1024 * 1024 * 1024  # 5GB
        elif variant_id == pro_id:
            plan = "pro"
            storage_limit = 50 * 1024 * 1024 * 1024  # 50GB
        else:
            return {"status": "ignored", "reason": "unknown variant"}
    
        # Update user plan
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {
                "$set": {
                    "plan": plan,
                    "storage_limit": storage_limit,
                    "api_calls_limit": -1,  # Unlimited
                    "lemon_subscription_id": attributes.get("id")
                }
            }
        )
    
        return {"status": "success", "event": "subscription_updated", "plan": plan}

    else:
        return {"status": "ignored", "event": event_name}


@router.get("/plans")
async def get_plans():
    """
    Get available subscription plans
    
    Returns:
        List of available plans with pricing
    """
    
    return {
        "plans": [
            {
                "id": "free",
                "name": "FREE",
                "price": "$0",
                "storage": "1GB",
                "api_calls": "10,000/month",
                "features": [
                    "1GB cloud storage",
                    "10,000 API calls per month",
                    "Basic support"
                ]
            },
            {
                "id": "starter",
                "name": "STARTER",
                "price": "$9/month",
                "storage": "5GB",
                "api_calls": "Unlimited",
                "features": [
                    "5GB cloud storage",
                    "Unlimited API calls",
                    "Priority support",
                    "Advanced features"
                ],
                "variant_id": os.getenv("LEMON_STARTER_VARIANT_ID")
            },
            {
                "id": "pro",
                "name": "PRO",
                "price": "$29/month",
                "storage": "50GB",
                "api_calls": "Unlimited",
                "features": [
                    "50GB cloud storage",
                    "Unlimited API calls",
                    "Premium support",
                    "All advanced features",
                    "Custom integrations"
                ],
                "variant_id": os.getenv("LEMON_PRO_VARIANT_ID")
            }
        ]
    }