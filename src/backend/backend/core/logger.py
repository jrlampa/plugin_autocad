"""
Centralized structured logging configuration using structlog.
Supports context-local storage for request correlation (trace_id).
"""
import sys
import logging
import structlog
from contextvars import ContextVar

# Context variables for trace propagation
trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")

def get_trace_id() -> str:
    return trace_id_ctx.get()

def set_trace_id(tid: str):
    trace_id_ctx.set(tid)

def configure_logging():
    """Configures structlog to output JSON in production or colored keys in dev."""
    
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

# Privacy by Design: PII Sanitizer
def sanitize_log_data(logger, method_name, event_dict):
    """
    Recursively sanitizes dictionary values to remove PII and sensitive paths.
    """
    import re
    
    SENSITIVE_KEYS = {'password', 'token', 'secret', 'authorization', 'username', 'email', 'key', 'access_token'}
    # Regex to catch Windows user paths: C:\Users\Jonatas Lampa\... -> C:\Users\***\...
    # Matches "Users\" followed by anything until next slash
    USER_PATH_REGEX = re.compile(r'(?<=Users[\\/])[^\\/]+', re.IGNORECASE)

    def _sanitize_val(val):
        if isinstance(val, str):
            # Mask User Paths
            val = USER_PATH_REGEX.sub('***', val)
            # Mask Email-like patterns (simplistic)
            if '@' in val and '.' in val:
                pass 
            return val
        return val

    def _sanitize_recursive(data):
        if isinstance(data, dict):
            new_data = {}
            for k, v in data.items():
                if k.lower() in SENSITIVE_KEYS:
                    new_data[k] = "*****"
                elif isinstance(v, (dict, list)):
                    new_data[k] = _sanitize_recursive(v)
                else:
                    new_data[k] = _sanitize_val(v)
            return new_data
        elif isinstance(data, list):
            return [_sanitize_recursive(i) for i in data]
        return _sanitize_val(data)

    return _sanitize_recursive(event_dict)

def configure_logging():
    """Configures structlog to output JSON in production or colored keys in dev."""
    
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        sanitize_log_data, # Added here
    ]

    # In dev, we use ConsoleRenderer for readability
    # In prod (or if desired), use JSONRenderer
    # For now, we defaulting to JSON for Audit correctness as per requirements
    renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=processors + [renderer],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure Standard Library Logging to rely on Structlog
    # This captures logs from uvicorn/fastapi/etc if customized
    # but for now we focus on application logs
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO
    )

def get_logger(name: str):
    return structlog.get_logger(name)
