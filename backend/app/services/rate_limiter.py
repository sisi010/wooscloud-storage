"""
Rate Limiter Service
Implements token bucket algorithm for API rate limiting
"""

from datetime import datetime, timedelta
from typing import Dict, Tuple
import asyncio
from collections import defaultdict

class InMemoryRateLimiter:
    """
    In-memory rate limiter using token bucket algorithm
    
    For production with multiple instances, use Redis instead
    """
    
    def __init__(self):
        # Format: {user_id: {window: {'count': int, 'reset_time': datetime}}}
        self.buckets: Dict[str, Dict[str, Dict]] = defaultdict(dict)
        self.lock = asyncio.Lock()
    
    async def check_rate_limit(
        self,
        user_id: str,
        plan: str,
        window: str = "hour"
    ) -> Tuple[bool, Dict[str, any]]:
        """
        Check if user has exceeded rate limit
        
        Args:
            user_id: User identifier
            plan: User's plan (free, starter, pro)
            window: Time window (hour, month)
            
        Returns:
            (allowed, info_dict) where info_dict contains:
            - limit: Maximum requests allowed
            - remaining: Requests remaining
            - reset: When the limit resets (timestamp)
        """
        
        # Get limits based on plan
        limits = self._get_limits(plan, window)
        
        async with self.lock:
            now = datetime.utcnow()
            
            # Get or create bucket
            if window not in self.buckets[user_id]:
                self.buckets[user_id][window] = {
                    'count': 0,
                    'reset_time': self._get_reset_time(now, window)
                }
            
            bucket = self.buckets[user_id][window]
            
            # Check if window expired - reset counter
            if now >= bucket['reset_time']:
                bucket['count'] = 0
                bucket['reset_time'] = self._get_reset_time(now, window)
            
            # Check limit
            allowed = bucket['count'] < limits
            
            # Increment counter if allowed
            if allowed:
                bucket['count'] += 1
            
            info = {
                'limit': limits,
                'remaining': max(0, limits - bucket['count']),
                'reset': int(bucket['reset_time'].timestamp()),
                'current': bucket['count']
            }
            
            return allowed, info
    
    def _get_limits(self, plan: str, window: str) -> int:
        """Get rate limits based on plan and window"""
        
        limits_config = {
            'free': {
                'hour': 100,
                'month': 10000
            },
            'starter': {
                'hour': 1000,
                'month': -1  # Unlimited
            },
            'pro': {
                'hour': 10000,
                'month': -1  # Unlimited
            }
        }
        
        plan = plan.lower()
        if plan not in limits_config:
            plan = 'free'
        
        limit = limits_config[plan].get(window, 100)
        return limit if limit > 0 else 999999999  # Unlimited
    
    def _get_reset_time(self, now: datetime, window: str) -> datetime:
        """Calculate when the limit resets"""
        
        if window == 'hour':
            # Reset at the start of next hour
            next_hour = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
            return next_hour
        
        elif window == 'month':
            # Reset at the start of next month
            if now.month == 12:
                next_month = now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                next_month = now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)
            return next_month
        
        else:
            # Default to 1 hour
            return now + timedelta(hours=1)
    
    async def get_stats(self, user_id: str) -> Dict[str, Dict]:
        """Get current rate limit stats for a user"""
        
        async with self.lock:
            stats = {}
            
            for window in ['hour', 'month']:
                if window in self.buckets.get(user_id, {}):
                    bucket = self.buckets[user_id][window]
                    stats[window] = {
                        'count': bucket['count'],
                        'reset_time': bucket['reset_time'].isoformat()
                    }
                else:
                    stats[window] = {
                        'count': 0,
                        'reset_time': None
                    }
            
            return stats

# Global instance
_rate_limiter = InMemoryRateLimiter()

def get_rate_limiter() -> InMemoryRateLimiter:
    """Get global rate limiter instance"""
    return _rate_limiter