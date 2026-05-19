"""Contract smoke tests for ``/api/craft/*``."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_craft_health_requires_token(anon_client):
    resp = await anon_client.get("/api/craft/health")
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_craft_health_ok(client):
    resp = await client.get("/api/craft/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "craft_aliases" in data
    assert "craft_recipes_resolved" in data


@pytest.mark.asyncio
async def test_craft_plan_create_minimal(client):
    resp = await client.post(
        "/api/craft/plan",
        json={"goal_alias_id": 1, "amount": 1, "client_id": "01"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    data = body["data"]
    assert "root_job_id" in data
    assert "plan_json" in data
    assert data["plan_json"]["stage"] == "failed"
