"""Smoke tests for new module endpoints."""

from __future__ import annotations

import json

import pytest


@pytest.mark.asyncio
async def test_robot_register_and_list(client):
    resp = await client.post(
        "/api/robots/register",
        json={"client_id": "robot_crop_01", "kind": "crop", "label": "South Field"},
    )
    assert resp.json()["code"] == 200

    listing = await client.get("/api/robots/list")
    body = listing.json()
    assert body["code"] == 200
    assert any(r["client_id"] == "robot_crop_01" for r in body["data"])


@pytest.mark.asyncio
async def test_robot_state_transitions(client):
    await client.post(
        "/api/robots/register",
        json={"client_id": "robot_miner_01", "kind": "miner"},
    )
    resp = await client.post(
        "/api/robots/robot_miner_01/state",
        json={"state": "moving", "last_message": "to target"},
    )
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["state"] == "moving"


@pytest.mark.asyncio
async def test_autocraft_pattern_upsert(client):
    payload = {
        "interface_address": "iface-test",
        "slot": 1,
        "kind": "processing",
        "inputs": [{"name": "minecraft:iron_ingot", "damage": 0, "amount": 1}],
        "outputs": [{"name": "minecraft:bucket", "damage": 0, "amount": 1}],
        "label": "Test bucket",
    }
    first = await client.post("/api/autocraft/patterns", json=payload)
    assert first.json()["code"] == 200
    second = await client.post("/api/autocraft/patterns", json=payload)
    assert second.json()["code"] == 200


@pytest.mark.asyncio
async def test_autocraft_program_pattern_enqueues_task(client):
    pattern_payload = {
        "interface_address": "iface-prog",
        "slot": 2,
        "kind": "processing",
        "inputs": [{"name": "minecraft:cobblestone", "damage": 0, "amount": 8}],
        "outputs": [{"name": "minecraft:stone", "damage": 0, "amount": 8}],
        "label": "Smelt cobble",
    }
    created = await client.post("/api/autocraft/patterns", json=pattern_payload)
    pattern_id = created.json()["data"]["id"]

    resp = await client.post(
        f"/api/autocraft/patterns/{pattern_id}/program",
        json={"client_id": "ae_oc_01"},
    )
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["task_id"] == f"pattern_{pattern_id}"
    cmds = body["data"]["commands"]
    assert any("ae.setMeInterfaceAddress('iface-prog')" in c for c in cmds)
    assert any("ae.programPattern(2" in c for c in cmds)


@pytest.mark.asyncio
async def test_autocraft_request_and_cancel(client):
    resp = await client.post(
        "/api/autocraft/request",
        json={
            "client_id": "ae_oc_01",
            "item_name": "gregtech:gt.metaitem.01",
            "item_damage": 11034,
            "amount": 5,
            "cpu_name": "Fast",
        },
    )
    body = resp.json()
    assert body["code"] == 200
    request_id = body["data"]["id"]

    cancel = await client.post(f"/api/autocraft/requests/{request_id}/cancel")
    assert cancel.json()["code"] == 200
    assert cancel.json()["data"]["request"]["state"] == "cancelling"


@pytest.mark.asyncio
async def test_autocraft_cpu_scan(client):
    resp = await client.post(
        "/api/autocraft/cpus/scan",
        json={"client_id": "ae_oc_01", "detail": True},
    )
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["task_id"].startswith("cpus_")


@pytest.mark.asyncio
async def test_autocraft_craft_report_updates_request_state(client):
    resp = await client.post(
        "/api/autocraft/request",
        json={
            "client_id": "ae_oc_01",
            "item_name": "minecraft:planks",
            "item_damage": 0,
            "amount": 1,
        },
    )
    body = resp.json()
    assert body["code"] == 200
    task_id = body["data"]["task_id"]
    request_id = body["data"]["id"]
    assert task_id.startswith("craft_")

    ok_payload = json.dumps(
        {"message": "success", "data": {"failed": False, "computing": False, "canceled": {"result": False}}}
    )
    report = await client.post(
        "/api/task/report",
        content=json.dumps({"task_id": task_id, "results": [ok_payload]}).encode("utf-8"),
    )
    assert report.json()["code"] == 200

    got = await client.get(f"/api/autocraft/requests/{request_id}")
    assert got.json()["data"]["state"] == "done"

    fail_payload = json.dumps({"message": "success", "data": {"failed": True}})
    resp2 = await client.post(
        "/api/autocraft/request",
        json={
            "client_id": "ae_oc_01",
            "item_name": "minecraft:stone",
            "item_damage": 0,
            "amount": 1,
        },
    )
    task2 = resp2.json()["data"]["task_id"]
    rid2 = resp2.json()["data"]["id"]
    await client.post(
        "/api/task/report",
        content=json.dumps({"task_id": task2, "results": [fail_payload]}).encode("utf-8"),
    )
    got2 = await client.get(f"/api/autocraft/requests/{rid2}")
    assert got2.json()["data"]["state"] == "failed"


@pytest.mark.asyncio
async def test_mining_jobs_next_and_patch(client):
    await client.post(
        "/api/robots/register",
        json={"client_id": "robot_miner_01", "kind": "miner"},
    )
    created = await client.post(
        "/api/robots/mining-jobs",
        json={
            "robot_client_id": "robot_miner_01",
            "dimension": 0,
            "x": 10,
            "y": 65,
            "z": -3,
            "miner_kind": "advanced_miner",
            "note": "test pit",
        },
    )
    assert created.json()["code"] == 200
    job_id = created.json()["data"]["id"]

    nxt = await client.get(
        "/api/robots/mining-jobs/next", params={"robot_client_id": "robot_miner_01"}
    )
    assert nxt.json()["code"] == 200
    assert nxt.json()["data"]["id"] == job_id

    patched = await client.patch(
        f"/api/robots/mining-jobs/{job_id}", json={"state": "running"}
    )
    body = patched.json()
    assert body["code"] == 200
    assert body["data"]["state"] == "running"
    assert body["data"]["started_at"] is not None


@pytest.mark.asyncio
async def test_mining_job_create_enqueues_oc_task(client):
    await client.post(
        "/api/robots/register",
        json={"client_id": "robot_miner_enqueue", "kind": "miner"},
    )
    created = await client.post(
        "/api/robots/mining-jobs",
        json={
            "robot_client_id": "robot_miner_enqueue",
            "dimension": 0,
            "x": 3227,
            "y": 73,
            "z": -4891,
            "miner_kind": "advanced_miner",
        },
    )
    body = created.json()
    assert body["code"] == 200
    assert body["data"]["state"] == "running"
    job_id = body["data"]["id"]

    fetched = await client.get(
        "/api/task/get", headers={"X-Client-ID": "robot_miner_enqueue"}
    )
    fbody = fetched.json()
    assert fbody["code"] == 200
    assert fbody["data"]["taskId"] == f"mining_job_{job_id}"
    assert "robot_miner.acceptJob" in fbody["data"]["commands"][0]

    enqueued = await client.post(f"/api/robots/mining-jobs/{job_id}/enqueue?deploy=true")
    assert enqueued.json()["code"] == 200


@pytest.mark.asyncio
async def test_power_jobs_next_and_patch(client):
    await client.post(
        "/api/robots/register",
        json={"client_id": "robot_power_01", "kind": "power"},
    )
    created = await client.post(
        "/api/robots/power-jobs",
        json={
            "robot_client_id": "robot_power_01",
            "dimension": 0,
            "x": 100,
            "y": 70,
            "z": 200,
            "generator_kind": "advanced_combustion_generator",
            "fuel_kind": "diesel",
            "capsule_count": 4,
            "note": "test gen",
        },
    )
    assert created.json()["code"] == 200
    job_id = created.json()["data"]["id"]

    nxt = await client.get(
        "/api/robots/power-jobs/next", params={"robot_client_id": "robot_power_01"}
    )
    assert nxt.json()["code"] == 200
    assert nxt.json()["data"]["id"] == job_id
    assert nxt.json()["data"]["fuel_kind"] == "diesel"

    patched = await client.patch(
        f"/api/robots/power-jobs/{job_id}", json={"state": "running"}
    )
    body = patched.json()
    assert body["code"] == 200
    assert body["data"]["state"] == "running"
    assert body["data"]["started_at"] is not None


@pytest.mark.asyncio
async def test_robots_list_route_not_shadowed_by_client_state(client):
    """Regression: /mining-jobs must not be captured as {client_id}/state."""

    r = await client.get("/api/robots/mining-jobs")
    assert r.status_code == 200
    assert r.json()["code"] == 200
    assert isinstance(r.json()["data"], list)

    r2 = await client.get("/api/robots/power-jobs")
    assert r2.status_code == 200
    assert r2.json()["code"] == 200
    assert isinstance(r2.json()["data"], list)


    obs = {
        "observations": [
            {"dimension": 0, "x": 1, "y": 60, "z": 1, "block_name": "minecraft:stone"},
            {"dimension": 0, "x": 1, "y": 60, "z": 2, "block_name": "gregtech:gt.blockores"},
        ]
    }
    resp = await client.post("/api/map/scan", json=obs)
    assert resp.json()["data"]["accepted"] == 2

    listing = await client.get("/api/map/blocks?dimension=0")
    assert listing.json()["code"] == 200
    assert len(listing.json()["data"]) >= 2
