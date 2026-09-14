"""Structured JSON access log for every HTTP request.

Emits one line after the response. The payload is an allowlist so passwords,
uploaded file contents, API keys, and environment values never appear in logs.
"""

from __future__ import annotations

import json
import logging
import time
import uuid

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)

LOG_FIELDS = (
    "request_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "user_id",
)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Attach a request_id and write one JSON access log per request."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            _emit_access_log(request, request_id, status_code, started)


def configure_request_logging(app: FastAPI) -> None:
    """Register access-log middleware so it wraps session and route handling."""
    app.add_middleware(RequestLoggingMiddleware)


def _emit_access_log(
    request: Request,
    request_id: str,
    status_code: int,
    started: float,
) -> None:
    payload = {
        "request_id": request_id,
        "method": request.method,
        "path": request.url.path,
        "status_code": status_code,
        "duration_ms": round((time.perf_counter() - started) * 1000, 3),
        "user_id": _user_id_from_session(request),
    }
    # Dump only the allowlisted fields, never request bodies or headers.
    logger.info(json.dumps({key: payload[key] for key in LOG_FIELDS}))


def _user_id_from_session(request: Request) -> int | None:
    try:
        user_id = request.session.get("user_id")
    except (AssertionError, AttributeError):
        return None
    if user_id is None:
        return None
    try:
        return int(user_id)
    except (TypeError, ValueError):
        return None
