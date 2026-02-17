import time
import functools
from enum import Enum
from typing import Callable, Any, Type
from backend.core.logger import get_logger

logger = get_logger(__name__)

class CircuitState(str, Enum):
    CLOSED = "closed"       # Normal operation
    OPEN = "open"           # Failing fast
    HALF_OPEN = "half_open" # Testing recovery

class CircuitBreakerOpenException(Exception):
    """Raised when the circuit is open and calls are blocked."""
    pass

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 30.0, exceptions: tuple = (Exception,)):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.exceptions = exceptions
        
        self.state = CircuitState.CLOSED
        self.failures = 0
        self.last_failure_time = 0.0
    
    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            self._check_state()
            
            if self.state == CircuitState.OPEN:
                logger.warning("circuit_open_access_denied", function=func.__name__)
                raise CircuitBreakerOpenException(f"Circuit '{func.__name__}' is OPEN")
            
            try:
                result = func(*args, **kwargs)
                self._on_success()
                return result
            except self.exceptions as e:
                self._on_failure()
                raise e
        return wrapper

    def _check_state(self):
        if self.state == CircuitState.OPEN:
            elapsed = time.time() - self.last_failure_time
            if elapsed > self.recovery_timeout:
                logger.info("circuit_half_open", previous="open")
                self.state = CircuitState.HALF_OPEN

    def _on_success(self):
        if self.state == CircuitState.HALF_OPEN:
            logger.info("circuit_closed", previous="half_open")
            self.state = CircuitState.CLOSED
            self.failures = 0
        elif self.state == CircuitState.CLOSED:
            # Reset failures on success just to be safe, 
            # though usually we only count consecutive failures or windowed
            self.failures = 0

    def _on_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        
        if self.state == CircuitState.HALF_OPEN:
            logger.warning("circuit_reopened", failures=self.failures)
            self.state = CircuitState.OPEN
        elif self.state == CircuitState.CLOSED:
            if self.failures >= self.failure_threshold:
                logger.warning("circuit_opened", failures=self.failures)
                self.state = CircuitState.OPEN
