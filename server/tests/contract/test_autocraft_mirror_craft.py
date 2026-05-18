"""Autocraft → craft domain mirror (gap plan §7 / C6)."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.db.models import CraftJob, CraftPlan
from app.db.session import AsyncSessionLocal


@pytest.mark.asyncio
async def test_autocraft_request_mirrors_craft_plan_and_job(client, nesql_db) -> None:
    r = await client.post(
        "/api/autocraft/request",
        json={
            "client_id": "oc_contract",
            "item_name": "item.IngotIron",
            "item_damage": 0,
            "amount": 2,
            "cpu_name": "TestCpu",
            "label": None,
        },
    )
    assert r.status_code == 200
    assert r.json()["code"] == 200
    task_id = r.json()["data"]["task_id"]
    assert task_id.startswith("craft_")

    async with AsyncSessionLocal() as session:
        job = (
            await session.execute(select(CraftJob).where(CraftJob.task_id == task_id))
        ).scalar_one()
        plan = await session.get(CraftPlan, job.plan_id)

    assert plan is not None
    assert plan.plan_json.get("legacy_autocraft") is True
    assert plan.root_job_id == job.id
    assert job.state == "programmed"
    assert job.goal_amount == 2
