"""SSE endpoint tests (plan B4)."""

from __future__ import annotations

import importlib
import pytest


@pytest.mark.asyncio
async def test_events_invalid_token_wrapped_json(anon_client):
    r = await anon_client.get("/api/events")
    assert r.status_code == 200
    body = r.json()
    assert body["code"] == 403


def test_sse_topic_filter_helpers():
    er = importlib.import_module("app.modules.events.router")
    assert er._parse_topic_filter("craft, robot ") == {"craft", "robot"}
    assert er._parse_topic_filter("") is None
    assert er._topic_allowed('{"topic":"craft","payload":{}}', {"craft"})
    assert not er._topic_allowed('{"topic":"craft","payload":{}}', {"robot"})
