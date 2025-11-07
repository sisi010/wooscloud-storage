"""
Rate Limit Middleware
Applies rate limiting to API requests
"""

from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
import logging

from app.services.rate_limiter import get_rate_limiter

logger = logging.getLogger(__name__)

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce rate limits on API requests
    
    Adds headers:
    - X-RateLimit-Limit: Maximum requests allowed
    - X-RateLimit-Remaining: Requests remaining
    - X-RateLimit-Reset: Unix timestamp when limit resets
    """
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks and docs
        if request.url.path in ["/", "/health", "/docs", "/openapi.json", "/redoc"]:
            return await call_next(request)
        
        # Skip if no user (will be caught by auth middleware)
        if not hasattr(request.state, "user"):
            return await call_next(request)
        
        user = request.state.user
        user_id = str(user.get("_id", ""))
        plan = user.get("plan", "free")
        
        # Check rate limit
        rate_limiter = get_rate_limiter()
        
        # Check hourly limit
        allowed, info = await rate_limiter.check_rate_limit(
            user_id=user_id,
            plan=plan,
            window="hour"
        )
        
        # Process request
        if allowed:
            response = await call_next(request)
        else:
            # Rate limit exceeded
            logger.warning(f"Rate limit exceeded for user {user_id} (plan: {plan})")
            
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "error": "Rate limit exceeded",
                    "limit": info['limit'],
                    "reset": info['reset'],
                    "retry_after": info['reset'] - int(datetime.utcnow().timestamp())
                }
            )
        
        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(info['limit'])
        response.headers["X-RateLimit-Remaining"] = str(info['remaining'])
        response.headers["X-RateLimit-Reset"] = str(info['reset'])
        
        return response


async def check_rate_limit_dependency(request: Request):
    """
    Dependency to check rate limit before processing request
    
    Can be used as a route dependency for specific endpoints
    """
    
    if not hasattr(request.state, "user"):
        return  # Will be caught by auth
    
    user = request.state.user
    user_id = str(user.get("_id", ""))
    plan = user.get("plan", "free")
    
    rate_limiter = get_rate_limiter()
    
    allowed, info = await rate_limiter.check_rate_limit(
        user_id=user_id,
        plan=plan,
        window="hour"
    )
    
    if not allowed:
        from datetime import datetime
        retry_after = info['reset'] - int(datetime.utcnow().timestamp())
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={
                "X-RateLimit-Limit": str(info['limit']),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(info['reset']),
                "Retry-After": str(retry_after)
            }
        )
    
    return info