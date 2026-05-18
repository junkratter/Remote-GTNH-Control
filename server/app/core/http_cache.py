"""HTTP cache headers for read-only NESQL and quest API responses."""

from __future__ import annotations

import hashlib
from pathlib import Path

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

import app.core.settings as settings_mod

CACHE_CONTROL = "public, max-age=86400, stale-while-revalidate=86400"

NesqlQuestsPrefixes = ("/api/nesql", "/api/quests")


def nesql_sqlite_path() -> Path | None:
    """Return path to nesql.sqlite if configured as SQLite."""
    url = settings_mod.settings.nesql_database_url
    if not url.startswith("sqlite:///"):
        return None
    p = Path(url.removeprefix("sqlite:///"))
    return p if p.exists() else None


def weak_etag_for_request(path: str, query_string: str, nesql_mtime: float) -> str:
    """Stable weak ETag from NESQL file mtime + URL path + query string.

    Mtime is rounded to whole seconds so WAL/auxiliary writes do not flip the ETag
    between back-to-back requests (same imported NESQL snapshot).
    """
    mtime_s = int(nesql_mtime)
    h = hashlib.sha256(
        f"{mtime_s}|{path}|{query_string}".encode("utf-8")
    ).hexdigest()[:24]
    return f'W/"{h}"'


class NesqlQuestsCacheMiddleware(BaseHTTPMiddleware):
    """Add Cache-Control + ETag; return 304 when If-None-Match matches."""

    async def dispatch(self, request: Request, call_next):
        if request.method != "GET":
            return await call_next(request)
        path = request.url.path
        if not any(path.startswith(p) for p in NesqlQuestsPrefixes):
            return await call_next(request)
        db_path = nesql_sqlite_path()
        if db_path is None:
            return await call_next(request)
        try:
            mtime = db_path.stat().st_mtime
        except OSError:
            return await call_next(request)
        qs = request.url.query or ""
        etag = weak_etag_for_request(path, qs, mtime)
        if_none = request.headers.get("if-none-match")
        if if_none and if_none.strip() == etag:
            return Response(
                status_code=304,
                headers={
                    "ETag": etag,
                    "Cache-Control": CACHE_CONTROL,
                },
            )
        response = await call_next(request)
        response.headers["Cache-Control"] = CACHE_CONTROL
        response.headers["ETag"] = etag
        return response
