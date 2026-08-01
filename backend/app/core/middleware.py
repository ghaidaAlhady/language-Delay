"""Request logging middleware.

Logs method, path, status code, and duration for every request — never the
request/response body, headers, or query string, so tokens, passwords, and
free-text answers never reach the logs even indirectly.
"""
from __future__ import annotations

import time
from uuid import uuid4

import structlog.contextvars
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        correlation_id = uuid4().hex
        request.state.correlation_id = correlation_id
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(correlation_id=correlation_id)
        started_at = time.perf_counter()
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = correlation_id
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            route = request.scope.get("route")
            route_template = getattr(route, "path", "unmatched")

            logger.info(
                "request_completed",
                method=request.method,
                route=route_template,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )
            return response
        finally:
            structlog.contextvars.clear_contextvars()
