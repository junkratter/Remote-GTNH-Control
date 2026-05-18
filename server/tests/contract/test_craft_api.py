"""Contract smoke tests for ``/api/craft/*``."""

from __future__ import annotations

import uuid

import pytest


@pytest.mark.asyncio
async def test_craft_aliases_create_and_plan_smoke(client):
    key = f"contract_alias_{uuid.uuid4().hex[:10]}"
    r = await client.post(
        "/api/craft/aliases",
        json={"key": key, "members": []},
    )
    assert r.status_code == 200
    assert r.json()["code"] == 200
    aid = r.json()["data"]["id"]

    r2 = await client.post(
        "/api/craft/plan",
        json={"goal_alias_id": aid, "amount": 1, "client_id": "oc_test"},
    )
    assert r2.status_code == 200
    body = r2.json()["data"]
    assert "root_job_id" in body
    assert body["state"] == "failed"

    tree = await client.get(f"/api/craft/plan/{body['root_job_id']}")
    assert tree.status_code == 200
    assert "jobs" in tree.json()["data"]
