"""
Centralized structured logging configuration using structlog.
Supports context-local storage for request correlation (trace_id).
"""
import re
import sys
import logging
from pathlib import Path
from logging.handlers import TimedRotatingFileHandler
from contextvars import ContextVar

try:
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False

# Context variables for trace propagation
trace_id_ctx: ContextVar[str] = ContextVar("trace_id", default="")

def get_trace_id() -> str:
    return trace_id_ctx.get()

def set_trace_id(tid: str):
    trace_id_ctx.set(tid)

# Privacy by Design: PII Sanitizer
_SENSITIVE_KEYS = frozenset({
    'password', 'token', 'secret', 'authorization',
    'username', 'email', 'key', 'access_token',
})
# Mask Windows user paths: C:\Users\<name>\... → C:\Users\***\...
_USER_PATH_RE = re.compile(r'(?<=Users[\\/])[^\\/]+', re.IGNORECASE)
# Mask email addresses: user@domain.tld → ***@domain.tld
_EMAIL_RE = re.compile(r'[^@\s]+(?=@[^@\s]+\.[^@\s]+)')


def _sanitize_val(val: object) -> object:
    if not isinstance(val, str):
        return val
    val = _USER_PATH_RE.sub('***', val)
    val = _EMAIL_RE.sub('***', val)
    return val


def _sanitize_recursive(data: object) -> object:
    if isinstance(data, dict):
        return {
            k: "*****" if k.lower() in _SENSITIVE_KEYS else _sanitize_recursive(v)
            for k, v in data.items()
        }
    if isinstance(data, list):
        return [_sanitize_recursive(i) for i in data]
    return _sanitize_val(data)


def sanitize_log_data(logger, method_name, event_dict):
    """Recursively sanitizes log event dict to remove PII and sensitive paths."""
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
        structlog.configure(
            processors=processors + [structlog.processors.JSONRenderer()],
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        handlers=[
            logging.StreamHandler(sys.stdout),
            TimedRotatingFileHandler(
                log_dir / "sisrua_backend.log",
                when="D",
                interval=1,
                backupCount=7,
            ),
        ],
    )


class CompatLogger:
    """Standard logging wrapper that mimics structlog's keyword argument support."""
    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def _fmt(self, event: str, kwargs: dict) -> str:
        return f"{event} {kwargs}" if kwargs else event

    def info(self, event: str, **kwargs):
        self._logger.info(self._fmt(event, kwargs))

    def warning(self, event: str, **kwargs):
        self._logger.warning(self._fmt(event, kwargs))

    def error(self, event: str, **kwargs):
        self._logger.error(self._fmt(event, kwargs))

    def debug(self, event: str, **kwargs):
        self._logger.debug(self._fmt(event, kwargs))


def get_logger(name: str):
    if HAS_STRUCTLOG:
        return structlog.get_logger(name)
    return CompatLogger(logging.getLogger(name))


def bind_contextvars(**kwargs):
    if HAS_STRUCTLOG:
        structlog.contextvars.bind_contextvars(**kwargs)
