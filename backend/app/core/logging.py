"""Structured JSON logging + request correlation for OrthoFlow backend.

Provides:
- JSON-formatted log output parseable by any log aggregator
- Correlation ID middleware (reads X-Correlation-ID or generates UUID)
- Request/response logging middleware with duration, user context
- PHI-safe error context helpers (never logs patient names, SSNs, DOBs)
"""

from __future__ import annotations

import json
import logging
import time
import traceback
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.types import ASGIApp

# ── Context Variables (async-safe, per-request) ──────────────────────────────

correlation_id_var: ContextVar[str] = ContextVar("correlation_id", default="none")
request_context_var: ContextVar[dict[str, Any]] = ContextVar("request_context", default={})

SERVICE_NAME = "orthoflow-backend"

# PHI fields that must NEVER appear in logs
_PHI_FIELDS: frozenset[str] = frozenset({
    "patient_name", "first_name", "last_name", "full_name",
    "ssn", "social_security", "date_of_birth", "dob",
    "phone", "email", "address", "insurance_id",
})


# ── JSON Log Formatter ───────────────────────────────────────────────────────

class StructuredJSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z",
            "level": record.levelname,
            "correlation_id": correlation_id_var.get("none"),
            "service": SERVICE_NAME,
            "module": record.module,
            "message": record.getMessage(),
        }

        # Attach structured context if provided via `extra={"context": {...}}`
        context = getattr(record, "context", None)
        if context:
            log_entry["context"] = _sanitize_phi(context)

        # Attach exception info if present
        if record.exc_info and record.exc_info[0] is not None:
            log_entry["error"] = _format_exception(record.exc_info)

        return json.dumps(log_entry, default=str, ensure_ascii=False)


# ── Logger Setup ─────────────────────────────────────────────────────────────

def setup_logging(level: str = "INFO") -> None:
    """Configure root logger with structured JSON output.

    Call once at application startup before any logging occurs.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Remove any existing handlers to avoid duplicate output
    root_logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setFormatter(StructuredJSONFormatter())
    root_logger.addHandler(handler)

    # Suppress noisy libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Get a named logger instance. Use module __name__ as the name."""
    return logging.getLogger(name)


# ── Correlation ID Middleware ────────────────────────────────────────────────

class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Extracts or generates a correlation ID for every request.

    - Reads from X-Correlation-ID header if present (for distributed tracing)
    - Otherwise generates a prefixed UUID: req-<short-uuid>
    - Sets the correlation ID in response headers for client-side tracing
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Extract or generate correlation ID
        incoming_id = request.headers.get("x-correlation-id")
        cid = incoming_id if incoming_id else f"req-{uuid.uuid4().hex[:12]}"

        # Set context var for downstream logging
        token = correlation_id_var.set(cid)

        try:
            response = await call_next(request)
            response.headers["X-Correlation-ID"] = cid
            return response
        finally:
            correlation_id_var.reset(token)


# ── Request/Response Logging Middleware ──────────────────────────────────────

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with method, path, status, duration, and user context.

    Skips health check endpoints to reduce noise.
    """

    SKIP_PATHS: frozenset[str] = frozenset({"/health", "/health/deep", "/openapi.json", "/docs", "/redoc"})

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)
        self._logger = get_logger("orthoflow.http")

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Skip noisy endpoints
        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        start_time = time.perf_counter()

        # Extract user_id from JWT if present (without failing on auth errors)
        user_id = _extract_user_id(request)

        # Store request context for error handlers
        ctx = {
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params) if request.query_params else None,
            "user_id": user_id,
            "client_ip": _get_client_ip(request),
        }
        ctx_token = request_context_var.set(ctx)

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            log_context = {
                **ctx,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            }

            if response.status_code >= 500:
                self._logger.error("Request failed", extra={"context": log_context})
            elif response.status_code >= 400:
                self._logger.warning("Client error", extra={"context": log_context})
            else:
                self._logger.info("Request completed", extra={"context": log_context})

            return response
        finally:
            request_context_var.reset(ctx_token)


# ── Error Context Helpers ────────────────────────────────────────────────────

def build_error_context(
    exc: BaseException,
    *,
    request: Request | None = None,
    max_frames: int = 5,
) -> dict[str, Any]:
    """Build a structured error context dict safe for logging.

    Args:
        exc: The exception that was raised.
        request: Optional FastAPI request for additional context.
        max_frames: Maximum traceback frames to include (default 5).

    Returns:
        Dict with error_type, message, traceback, and request context.
    """
    # Get traceback frames, truncated
    tb_lines = traceback.format_exception(type(exc), exc, exc.__traceback__)
    # Extract individual frame lines and limit
    frames = [
        line.strip()
        for line in traceback.format_tb(exc.__traceback__)
    ][-max_frames:]

    error_ctx: dict[str, Any] = {
        "error_type": type(exc).__qualname__,
        "message": str(exc),
        "traceback_frames": frames,
    }

    # Add request context if available
    if request:
        error_ctx["request"] = {
            "method": request.method,
            "path": request.url.path,
            "query": str(request.query_params) if request.query_params else None,
            "user_id": _extract_user_id(request),
            "client_ip": _get_client_ip(request),
        }
    else:
        # Fall back to context var if no request passed directly
        req_ctx = request_context_var.get({})
        if req_ctx:
            error_ctx["request"] = req_ctx

    return _sanitize_phi(error_ctx)


def log_error(
    logger: logging.Logger,
    message: str,
    exc: BaseException,
    *,
    request: Request | None = None,
    extra_context: dict[str, Any] | None = None,
) -> None:
    """Log an error with full structured context.

    Convenience function that combines error context building with logging.
    """
    context = build_error_context(exc, request=request)
    if extra_context:
        context["extra"] = _sanitize_phi(extra_context)

    logger.error(message, extra={"context": context})


# ── PHI Sanitization ─────────────────────────────────────────────────────────

def _sanitize_phi(data: Any) -> Any:
    """Recursively strip PHI fields from log context.

    Replaces PHI values with '[REDACTED]' to comply with HIPAA.
    Allows patient_id through (non-PHI identifier).
    """
    if isinstance(data, dict):
        return {
            k: "[REDACTED]" if k.lower() in _PHI_FIELDS else _sanitize_phi(v)
            for k, v in data.items()
        }
    elif isinstance(data, list):
        return [_sanitize_phi(item) for item in data]
    return data


# ── Internal Helpers ─────────────────────────────────────────────────────────

def _extract_user_id(request: Request) -> str | None:
    """Extract user_id from JWT in Authorization header without raising.

    Returns None if no valid token present — this is expected for
    unauthenticated endpoints.
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    try:
        from jose import jwt as jose_jwt
        from app.core.config import settings

        token = auth_header[7:]  # Strip "Bearer "
        payload = jose_jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload.get("sub")
    except Exception:
        return None


def _get_client_ip(request: Request) -> str:
    """Get client IP, respecting X-Forwarded-For from reverse proxy."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _format_exception(exc_info: tuple) -> dict[str, Any]:
    """Format exception info tuple into structured dict."""
    exc_type, exc_value, exc_tb = exc_info
    frames = traceback.format_tb(exc_tb)[-5:]  # Last 5 frames
    return {
        "error_type": exc_type.__qualname__ if exc_type else "Unknown",
        "message": str(exc_value) if exc_value else "",
        "traceback_frames": [f.strip() for f in frames],
    }
