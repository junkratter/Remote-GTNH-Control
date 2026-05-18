"""Contract regression for /api/task/*.

If anything here breaks, the live OC client (Lua) in Minecraft will
stop working. Update with care and only alongside `oc-client/` changes.
"""

from __future__ import annotations

import json

import pytest


HEADERS_TOKEN = {"X-Server-Token": "test-token"}


@pytest.mark.asyncio
async def test_get_requires_token(anon_client):
    resp = await anon_client.get("/api/task/get")
    assert resp.status_code == 422  # missing header


@pytest.mark.asyncio
async def test_get_rejects_wrong_token(anon_client):
    resp = await anon_client.get("/api/task/get", headers={"X-Server-Token": "nope"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 403
    assert body["data"] is None


@pytest.mark.asyncio
async def test_get_returns_empty_when_no_tasks(client):
    resp = await client.get("/api/task/get", headers={"X-Client-ID": "client_test"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 200
    assert body["data"] is None
    assert "message" in body


@pytest.mark.asyncio
async def test_add_get_report_roundtrip(client):
    add = await client.post(
        "/api/task/add",
        json={"task_id": "contract_test", "client_id": "client_test", "commands": ["return 1"]},
    )
    assert add.json()["code"] == 200

    fetched = await client.get(
        "/api/task/get", headers={"X-Client-ID": "client_test"}
    )
    payload = fetched.json()
    assert payload["code"] == 200
    assert payload["data"]["taskId"] == "contract_test"
    assert payload["data"]["commands"] == ["return 1"]
    assert payload["data"]["is_chunked"] is False

    reported = await client.post(
        "/api/task/report",
        content=json.dumps({"task_id": "contract_test", "results": ["1"]}).encode("utf-8"),
        headers={**HEADERS_TOKEN, "X-Client-ID": "client_test"},
    )
    assert reported.json()["code"] == 200

    status = await client.get("/api/task/status?task_id=contract_test&remove=false")
    sbody = status.json()
    assert sbody["code"] == 200
    assert sbody["data"]["status"] == "completed"
    assert sbody["data"]["result"] == ["1"]


@pytest.mark.asyncio
async def test_chunked_report_flow(client):
    await client.post(
        "/api/task/add",
        json={
            "task_id": "contract_chunked",
            "client_id": "client_chunked",
            "commands": ["return ae.getAllItems()"],
        },
    )
    await client.get("/api/task/get", headers={"X-Client-ID": "client_chunked"})

    body1 = json.dumps({"task_id": "contract_chunked", "results": [{"i": 1}, {"i": 2}]}).encode()
    r1 = await client.post(
        "/api/task/chunked_report?chunked=1",
        content=body1,
        headers={"X-Client-ID": "client_chunked"},
    )
    assert r1.json()["code"] == 200

    body2 = json.dumps({"task_id": "contract_chunked", "results": [{"i": 3}]}).encode()
    r2 = await client.post(
        "/api/task/chunked_report?chunked=2",
        content=body2,
        headers={"X-Client-ID": "client_chunked"},
    )
    assert r2.json()["code"] == 200

    body3 = json.dumps({"task_id": "contract_chunked", "results": [{"i": 4}]}).encode()
    r3 = await client.post(
        "/api/task/chunked_report?chunked=0",
        content=body3,
        headers={"X-Client-ID": "client_chunked"},
    )
    assert r3.json()["code"] == 200

    status = await client.get("/api/task/status?task_id=contract_chunked&remove=false")
    sbody = status.json()
    assert sbody["data"]["status"] == "completed"
    assert sbody["data"]["result"] == [{"i": 1}, {"i": 2}, {"i": 3}, {"i": 4}]


@pytest.mark.asyncio
async def test_cached_task_refresh_clears_previous_results(client):
    """Regression: getAllItems cache=True must not append to stale results."""

    await client.post("/api/task/task", json={"task_id": "getAllItems"})
    body = json.dumps(
        {"task_id": "getAllItems", "results": [{"name": "minecraft:stone", "size": 1}]}
    ).encode()
    await client.post("/api/task/chunked_report?chunked=1", content=body)
    await client.post("/api/task/chunked_report?chunked=0", content=body)

    status1 = await client.get("/api/task/status?task_id=getAllItems&remove=false")
    assert len(status1.json()["data"]["result"]) == 1

    await client.post("/api/task/task", json={"task_id": "getAllItems"})
    body2 = json.dumps(
        {
            "task_id": "getAllItems",
            "results": [
                {"name": "minecraft:dirt", "size": 2},
                {"name": "minecraft:gravel", "size": 3},
            ],
        }
    ).encode()
    await client.post("/api/task/chunked_report?chunked=1", content=body2)
    await client.post("/api/task/chunked_report?chunked=0", content=body2)

    status2 = await client.get("/api/task/status?task_id=getAllItems&remove=false")
    names = {row["name"] for row in status2.json()["data"]["result"]}
    assert names == {"minecraft:dirt", "minecraft:gravel"}


@pytest.mark.asyncio
async def test_chunked_report_flattens_nested_arrays(client):
    """OC may send each chunk as a single element wrapping the full item list."""

    await client.post("/api/task/task", json={"task_id": "getAllItems", "client_id": "client_nested"})
    await client.get("/api/task/get", headers={"X-Client-ID": "client_nested"})

    full = [{"name": "a", "size": 1}, {"name": "b", "size": 2}]
    for chunked in (1, 2, 0):
        payload = json.dumps({"task_id": "getAllItems", "results": [full]}).encode()
        r = await client.post(
            f"/api/task/chunked_report?chunked={chunked}",
            content=payload,
            headers={"X-Client-ID": "client_nested"},
        )
        assert r.json()["code"] == 200

    status = await client.get("/api/task/status?task_id=getAllItems&remove=false")
    assert status.json()["data"]["result"] == [
        {"name": "a", "size": 1},
        {"name": "b", "size": 2},
    ]


@pytest.mark.asyncio
async def test_task_by_name_uses_config(client):
    resp = await client.post(
        "/api/task/task",
        json={"task_id": "getCpuList", "client_id": "client_named"},
    )
    body = resp.json()
    assert body["code"] == 200
    assert body["data"]["taskId"] == "getCpuList"

    fetched = (
        await client.get("/api/task/get", headers={"X-Client-ID": "client_named"})
    ).json()
    assert fetched["data"]["taskId"] == "getCpuList"
    assert "return ae.getCpuList()" in fetched["data"]["commands"][0]


@pytest.mark.asyncio
async def test_info_version_is_public(anon_client):
    resp = await anon_client.get("/api/info/version")
    body = resp.json()
    assert body["code"] == 200
    assert "version" in body["data"]
