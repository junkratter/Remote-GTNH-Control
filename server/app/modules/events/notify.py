"""Fan-out craft/domain notifications (Redis pub/sub + PostgreSQL NOTIFY, plan B4)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import text

from app.core.logging import logger
from app.db.session import engine

# Redis: SSE subscribes here when ``app.state.redis`` is set.
REDIS_EVENTS_CHANNEL = "gtnh:events"

# PostgreSQL: payload passed to ``pg_notify`` (SSE LISTEN when no Redis).
PG_NOTIFY_CHANNEL = "remote_gtnh_control_events"

# PostgreSQL notifies are limited; keep headroom below 8000-byte server limit.
_MAX_PG_PAYLOAD = 7800


def _truncated_json(topic: str, payload: dict[str, Any]) -> str:
    base = json.dumps({"topic": topic, "payload": payload}, separators=(",", ":"), default=str)
    if len(base) <= _MAX_PG_PAYLOAD:
        return base
    small = json.dumps(
        {"topic": topic, "payload": {"error": "payload_truncated"}},
        separators=(",", ":"),
    )
    if len(small) <= _MAX_PG_PAYLOAD:
        logger.warning(
            "notify: craft payload exceeded pg_notify size; sent stub topic=%s", topic
        )
        return small
    return json.dumps(
        {"topic": "system", "payload": {"error": "notify_too_large"}},
        separators=(",", ":"),
    )


async def notify(app: Any | None, topic: str, payload: dict[str, Any]) -> None:
    """Publish an event to optional Redis and (on Postgres) ``pg_notify``."""

    if app is None:
        return
    body = _truncated_json(topic, payload)

    redis = getattr(app.state, "redis", None)
    if redis is not None:
        try:
            await redis.publish(REDIS_EVENTS_CHANNEL, body)
        except Exception:
            logger.exception("notify: redis publish failed topic=%s", topic)

    if engine.sync_engine.dialect.name != "postgresql":
        return

    try:
        async with engine.begin() as conn:
            await conn.execute(
                text("SELECT pg_notify(:channel, :payload)"),
                {"channel": PG_NOTIFY_CHANNEL, "payload": body},
            )
    except Exception:
        logger.exception("notify: pg_notify failed topic=%s", topic)
