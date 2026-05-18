"""Server-Sent Events stream (plan B4): ping, optional Redis or Postgres fan-in."""

from __future__ import annotations

import asyncio
import contextlib
import json
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

import app.core.settings as settings_mod
from app.modules.events.notify import PG_NOTIFY_CHANNEL, REDIS_EVENTS_CHANNEL

router = APIRouter()

PING_INTERVAL_SEC = 15.0


def _parse_topic_filter(topics: str) -> set[str] | None:
    items = {t.strip() for t in topics.split(",") if t.strip()}
    return items or None


def _topic_allowed(raw: str, topic_filter: set[str] | None) -> bool:
    if topic_filter is None:
        return True
    try:
        obj = json.loads(raw)
        t = obj.get("topic")
        return t in topic_filter
    except (json.JSONDecodeError, TypeError):
        return False


def _asyncpg_dsn() -> str | None:
    url = settings_mod.settings.database_url
    if "sqlite" in url:
        return None
    if url.startswith("postgresql+asyncpg://"):
        return "postgresql://" + url.removeprefix("postgresql+asyncpg://")
    if url.startswith("postgresql://"):
        return url
    return None


async def _redis_subscription(
    redis: Any,
    queue: asyncio.Queue[str | None],
    topic_filter: set[str] | None,
    stop: asyncio.Event,
) -> None:
    pubsub = redis.pubsub()
    try:
        await pubsub.subscribe(REDIS_EVENTS_CHANNEL)
        async for msg in pubsub.listen():
            if stop.is_set():
                break
            if msg.get("type") != "message":
                continue
            data = msg.get("data")
            if not isinstance(data, str):
                continue
            if _topic_allowed(data, topic_filter):
                await queue.put(data)
    finally:
        with contextlib.suppress(Exception):
            await pubsub.unsubscribe(REDIS_EVENTS_CHANNEL)
        with contextlib.suppress(Exception):
            await pubsub.close()


async def _postgres_notifications(
    dsn: str,
    queue: asyncio.Queue[str | None],
    topic_filter: set[str] | None,
    stop: asyncio.Event,
) -> None:
    import asyncpg

    conn = await asyncpg.connect(dsn)
    loop = asyncio.get_running_loop()

    async def _push_payload(payload: str | None) -> None:
        if payload and _topic_allowed(payload, topic_filter):
            await queue.put(payload)

    def _on_notify(_con: Any, _pid: int, _channel: str, payload: str) -> None:
        asyncio.run_coroutine_threadsafe(_push_payload(payload), loop)

    await conn.add_listener(PG_NOTIFY_CHANNEL, _on_notify)
    try:
        while not stop.is_set():
            await asyncio.sleep(1.0)
    finally:
        with contextlib.suppress(Exception):
            await conn.remove_listener(PG_NOTIFY_CHANNEL, _on_notify)
        with contextlib.suppress(Exception):
            await conn.close()


async def _pinger(
    queue: asyncio.Queue[str | None],
    stop: asyncio.Event,
    interval: float,
) -> None:
    while not stop.is_set():
        await asyncio.sleep(interval)
        if stop.is_set():
            break
        await queue.put(None)


@router.get("/events")
async def events_sse(
    request: Request,
    token: str | None = Query(None, description="Same as X-Server-Token (EventSource sends no headers)."),
    topics: str = Query("", description="Comma-separated topic names (filter). Empty = all topics."),
) -> StreamingResponse:
    if not token or token != settings_mod.settings.server_token:
        raise HTTPException(status_code=403, detail="Invalid or missing token")

    topic_filter = _parse_topic_filter(topics)
    app = request.app
    redis = getattr(app.state, "redis", None)
    pg_dsn = None if redis else _asyncpg_dsn()

    async def gen() -> AsyncIterator[bytes]:
        queue: asyncio.Queue[str | None] = asyncio.Queue()
        stop = asyncio.Event()
        tasks: list[asyncio.Task[Any]] = []

        tasks.append(
            asyncio.create_task(
                _pinger(queue, stop, PING_INTERVAL_SEC),
                name="sse-ping",
            )
        )
        if redis is not None:
            tasks.append(
                asyncio.create_task(
                    _redis_subscription(redis, queue, topic_filter, stop),
                    name="sse-redis",
                )
            )
        elif pg_dsn:
            tasks.append(
                asyncio.create_task(
                    _postgres_notifications(pg_dsn, queue, topic_filter, stop),
                    name="sse-pg",
                )
            )

        try:
            while True:
                item = await queue.get()
                if item is None:
                    yield b": ping\n\n"
                else:
                    yield f"data: {item}\n\n".encode()
        finally:
            stop.set()
            for t in tasks:
                t.cancel()
            for t in tasks:
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await t

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
