"""Optional one-line HTTP access logs (method, path, client, X-Client-ID)."""

from __future__ import annotations

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.settings import settings

_access_logger = logging.getLogger("remote-gtnh-control.access")


class HttpAccessLogMiddleware(BaseHTTPMiddleware):
    """Logs each request/response when ``settings.access_log_http`` is true."""

    async def dispatch(self, request: Request, call_next) -> Response:
        client_host = request.client.host if request.client else "-"
        client_id = request.headers.get("X-Client-ID", "-")
        path = request.url.path
        _access_logger.info(
            "http %s %s from=%s X-Client-ID=%s",
            request.method,
            path,
            client_host,
            client_id,
        )
        response = await call_next(request)
        _access_logger.info(
            "http %s %s -> %s",
            request.method,
            path,
            response.status_code,
        )
        return response


def install_http_access_log(app) -> None:
    """Register access-log middleware if enabled in settings."""
    if settings.access_log_http:
        app.add_middleware(HttpAccessLogMiddleware)
