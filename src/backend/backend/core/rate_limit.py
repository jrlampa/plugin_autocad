
import time
import threading
from typing import Dict, Tuple
from fastapi import HTTPException, Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware

class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        """
        capacity: Max tokens in the bucket.
        refill_rate: Tokens added per second.
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = float(capacity)
        self.last_update = time.time()
        self.lock = threading.Lock()

    def consume(self, tokens: int = 1) -> Tuple[bool, Dict[str, any]]:
        """Returns (allowed, rate_limit_info)"""
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now
            
            # Refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            
            rate_info = {
                "limit": self.capacity,
                "remaining": int(self.tokens),
                "reset": int(now + (self.capacity - self.tokens) / self.refill_rate)
            }
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                rate_info["remaining"] = int(self.tokens)
                return True, rate_info
            
            rate_info["remaining"] = 0
            rate_info["retry_after"] = int((1.0 - self.tokens) / self.refill_rate)
            return False, rate_info

# Simple in-memory store for IP-based limits
# Key: IP Address, Value: TokenBucket
_limiters: Dict[str, TokenBucket] = {}
_limiter_lock = threading.Lock()

class RateLimiter:
    def __init__(self, calls: int, period: int = 60):
        """
        calls: Number of allowed calls in 'period' seconds.
        """
        self.capacity = calls
        self.refill_rate = calls / float(period)

    async def __call__(self, request: Request):
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{self.capacity}:{self.refill_rate}"
        
        with _limiter_lock:
            if key not in _limiters:
                _limiters[key] = TokenBucket(self.capacity, self.refill_rate)
            bucket = _limiters[key]
        
        allowed, rate_info = bucket.consume(1)
        
        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down.",
                headers={
                    "X-RateLimit-Limit": str(rate_info["limit"]),
                    "X-RateLimit-Remaining": str(rate_info["remaining"]),
                    "X-RateLimit-Reset": str(rate_info["reset"]),
                    "Retry-After": str(rate_info.get("retry_after", 60))
                }
            )
        
        # Store rate info in request state for middleware to add headers
        request.state.rate_limit_info = rate_info


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to add rate limit headers to all responses."""
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # Add rate limit headers if available
        if hasattr(request.state, "rate_limit_info"):
            info = request.state.rate_limit_info
            response.headers["X-RateLimit-Limit"] = str(info["limit"])
            response.headers["X-RateLimit-Remaining"] = str(info["remaining"])
            response.headers["X-RateLimit-Reset"] = str(info["reset"])
        
        return response

