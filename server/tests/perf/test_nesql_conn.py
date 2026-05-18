"""Shared NESQL connection: concurrent reads should not block health (plan A2)."""

from __future__ import annotations

import asyncio

import pytest


@pytest.mark.asyncio
async def test_parallel_nesql_does_not_block_health(client, nesql_db):
    """Many concurrent NESQL reads; a health check interleaved completes."""

    async def burst_items():
        for _ in range(40):
            await client.get("/api/nesql/items", params={"q": "iron"})

    async def ping():
        await client.get("/health")

    await asyncio.gather(burst_items(), burst_items(), ping(), burst_items())
