"""Integration tests for /api/map/* (Phase 5 world_blocks + geolyzer ingest)."""

from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_map_scan_upsert_and_list(client):
    payload = {
        "observations": [
            {
                "dimension": 0,
                "x": 10,
                "y": 64,
                "z": -3,
                "block_name": "minecraft:stone",
                "hardness": 1.5,
                "fluid": None,
                "meta": {"src": "test"},
            }
        ]
    }
    r1 = await client.post("/api/map/scan", json=payload)
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["code"] == 200
    assert body1["data"]["accepted"] == 1

    # Upsert same cell with different block name
    payload["observations"][0]["block_name"] = "minecraft:iron_ore"
    r2 = await client.post("/api/map/scan", json=payload)
    assert r2.json()["data"]["accepted"] == 1

    listed = await client.get("/api/map/blocks", params={"dimension": 0, "limit": 100})
    assert listed.status_code == 200
    data = listed.json()["data"]
    assert len(data) >= 1
    cell = next(b for b in data if b["x"] == 10 and b["y"] == 64 and b["z"] == -3)
    assert cell["block_name"] == "minecraft:iron_ore"
    assert cell["hardness"] == 1.5

    by_name = await client.get(
        "/api/map/blocks",
        params={"dimension": 0, "block_name": "minecraft:iron_ore", "limit": 50},
    )
    assert by_name.status_code == 200
    assert any(b["x"] == 10 for b in by_name.json()["data"])


@pytest.mark.asyncio
async def test_map_scan_requires_token(anon_client):
    r = await anon_client.post(
        "/api/map/scan",
        json={"observations": [{"dimension": 0, "x": 0, "y": 0, "z": 0}]},
    )
    # Missing X-Server-Token is a client error (422) before route handler runs.
    assert r.status_code in (401, 403, 422)
