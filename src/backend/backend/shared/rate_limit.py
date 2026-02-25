
import time
import threading
from typing import Dict, Tuple
from fastapi import HTTPException, Request, status

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

    def consume(self, tokens: int = 1) -> bool:
        with self.lock:
            now = time.time()
            elapsed = now - self.last_update
            self.last_update = now
            
            # Refill
            self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False

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
        
        if not bucket.consume(1):
             raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down."
            )
