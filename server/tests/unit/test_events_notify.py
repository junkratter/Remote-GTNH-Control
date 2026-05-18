"""Unit tests for :func:`notify` (plan B4)."""

from __future__ import annotations

import json
import pytest


@pytest.mark.asyncio
async def test_notify_redis_publish(app):
    from app.modules.events.notify import REDIS_EVENTS_CHANNEL, notify

    calls: list[tuple[str, str]] = []

    class FakeRedis:
        async def publish(self, channel: str, body: str) -> None:
            calls.append((channel, body))

    app.state.redis = FakeRedis()
    await notify(app, "craft", {"k": 1})
    assert len(calls) == 1
    assert calls[0][0] == REDIS_EVENTS_CHANNEL
    obj = json.loads(calls[0][1])
    assert obj["topic"] == "craft"
    assert obj["payload"] == {"k": 1}
    app.state.redis = None


@pytest.mark.asyncio
async def test_notify_skips_when_app_none():
    from app.modules.events.notify import notify

    await notify(None, "x", {})  # does not raise
