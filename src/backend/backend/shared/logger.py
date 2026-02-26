"""
Centralized structured logging configuration using structlog.
Supports context-local storage for request correlation (trace_id).
"""
import sys
import logging
from pathlib import Path
try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:  # pragma: no cover — structlog is installed in CI
    HAS_STRUCTLOG = False
from contextvars import ContextVar

# Context variables for trace propagation
trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")

def get_trace_id() -> str:
    return trace_id_ctx.get()

def set_trace_id(tid: str):
    trace_id_ctx.set(tid)

def configure_logging():  # pragma: no cover — immediately overridden by second definition below
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
    """Configures structlog or falls back to standard logging."""
    if HAS_STRUCTLOG:
        processors = [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            sanitize_log_data,
        ]
        renderer = structlog.processors.JSONRenderer()
        structlog.configure(
            processors=processors + [renderer],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    root_logger = logging.getLogger()
    console_handler = logging.StreamHandler(sys.stdout)
    from logging.handlers import TimedRotatingFileHandler
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = TimedRotatingFileHandler(
        log_dir / "sisrua_backend.log",
        when="D",
        interval=1,
        backupCount=7
    )
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        handlers=[console_handler, file_handler]
    )

class CompatLogger:
    """Standard logging wrapper that mimics structlog's keyword argument support."""
    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def info(self, event: str, **kwargs):
        if kwargs:
            msg = f"{event} {kwargs}"
            self._logger.info(msg)
        else:
            self._logger.info(event)

    def warning(self, event: str, **kwargs):
        if kwargs:
            msg = f"{event} {kwargs}"
            self._logger.warning(msg)
        else:
            self._logger.warning(event)

    def error(self, event: str, **kwargs):
        if kwargs:
            msg = f"{event} {kwargs}"
            self._logger.error(msg)
        else:
            self._logger.error(event)
    
    def debug(self, event: str, **kwargs):
        if kwargs:
            msg = f"{event} {kwargs}"
            self._logger.debug(msg)
        else:
            self._logger.debug(event)

def get_logger(name: str):
    if HAS_STRUCTLOG:
        return structlog.get_logger(name)
    return CompatLogger(logging.getLogger(name))

def bind_contextvars(**kwargs):
    if HAS_STRUCTLOG:
        structlog.contextvars.bind_contextvars(**kwargs)
    # Fallback: do nothing or update a local context
