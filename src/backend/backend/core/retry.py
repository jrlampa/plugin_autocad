
import time
import functools
import random
from typing import Callable, Any, Tuple, Type
from backend.core.logger import get_logger

logger = get_logger(__name__)

class Retry:
    """
    Decorator for exponential backoff retries.
    
    Usage:
        @Retry(max_retries=3, backoff_factor=1.5, initial_delay=1.0)
        def my_func():
            ...
    """
    def __init__(
        self, 
        max_retries: int = 3, 
        initial_delay: float = 1.0, 
        backoff_factor: float = 2.0, 
        jitter: bool = True,
        exceptions: Tuple[Type[Exception], ...] = (Exception,)
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.backoff_factor = backoff_factor
        self.jitter = jitter
        self.exceptions = exceptions

    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            attempt = 0
            delay = self.initial_delay
            
            while True:
                try:
                    return func(*args, **kwargs)
                except self.exceptions as e:
                    attempt += 1
                    if attempt > self.max_retries:
                        logger.warning("retry_gave_up", function=func.__name__, attempts=attempt, error=str(e))
                        raise e
                    
                    # Calculate next delay
                    sleep_time = delay
                    if self.jitter:
                        sleep_time *= (0.5 + random.random()) # 0.5x to 1.5x jitter
                        
                    logger.info("retry_backing_off", function=func.__name__, attempt=attempt, sleep_time=f"{sleep_time:.2f}s", error=str(e))
                    time.sleep(sleep_time)
                    
                    delay *= self.backoff_factor
                    
        return wrapper
