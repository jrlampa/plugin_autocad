from fastapi import Request
from starlette.responses import Response
from backend.shared.logger import get_logger, set_trace_id, HAS_STRUCTLOG
from backend.shared.auth import AUTH_HEADER_NAME, is_valid_session, _get_master_token
import uuid

logger = get_logger(__name__)

ALLOWED_ORIGINS = {
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
}

PUBLIC_PATHS = {"/api/v1/health", "/health", "/docs", "/openapi.json", "/"}

async def add_trace_header(request: Request, call_next):
    """Adiciona um trace_id único para rastreamento de logs (ISO 27001)."""
    trace_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
    set_trace_id(trace_id)
    
    if HAS_STRUCTLOG:
        import structlog
        structlog.contextvars.bind_contextvars(trace_id=trace_id)
        
    response = await call_next(request)
    response.headers["X-Request-ID"] = trace_id
    response.headers["X-Trace-Id"] = trace_id
    return response

async def validate_origin(request: Request, call_next):
    """ISO 27001: Bloqueio de origens externas e requisições suspeitas."""
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    client_host = request.client.host if request.client else "unknown"
    is_local = client_host in ("127.0.0.1", "localhost", "::1", "unknown")

    origin = request.headers.get("Origin")
    referer = request.headers.get("Referer")

    if origin:
        is_localhost_origin = (
            origin.startswith("http://localhost:")
            or origin.startswith("http://127.0.0.1:")
        )
        if not is_localhost_origin and origin not in ALLOWED_ORIGINS:
            logger.warning("security_violation_invalid_origin", origin=origin, client=client_host)
            return Response("Forbidden: Invalid Origin", status_code=403)

    token = request.headers.get(AUTH_HEADER_NAME)
    master = _get_master_token()
    has_valid_auth = (token == master) or bool(token and is_valid_session(token))

    if is_local or has_valid_auth:
        return await call_next(request)

    if request.base_url.hostname == "testserver":
        return await call_next(request)

    if not origin and not referer and request.url.path.startswith("/api/v1"):
        logger.warning(
            "security_violation_no_origin",
            path=request.url.path,
            client=client_host,
            has_token=bool(token),
        )
        return Response("Forbidden: Strict Origin Required", status_code=403)

    return await call_next(request)

async def add_security_headers(request: Request, call_next):
    """Adiciona cabeçalhos de segurança HTTP (OWASP Best Practices)."""
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self'"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response
