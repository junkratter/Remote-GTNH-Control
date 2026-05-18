"""Device (OC client) tracking — replaces the legacy `utils/device.py`."""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Device


MAX_RECENT_RECORDS = 10


def _now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class DeviceManager:
    async def record(
        self,
        session: AsyncSession,
        client_id: str | None,
        kind: str = "get",
    ) -> None:
        if not client_id:
            return
        device = await session.get(Device, client_id)
        record = {"time": _now().isoformat(), "type": kind}
        if device is None:
            device = Device(
                id=client_id,
                first_seen=_now(),
                last_seen=_now(),
                recent_activity=[record],
            )
            session.add(device)
        else:
            recent = list(device.recent_activity or [])
            recent.append(record)
            if len(recent) > MAX_RECENT_RECORDS:
                recent = recent[-MAX_RECENT_RECORDS:]
            device.recent_activity = recent
            device.last_seen = _now()
        await session.commit()

    async def list(self, session: AsyncSession) -> list[dict[str, Any]]:
        rows = await session.execute(select(Device))
        return [
            {
                "id": d.id,
                "first_seen": d.first_seen.isoformat() if d.first_seen else None,
                "last_seen": d.last_seen.isoformat() if d.last_seen else None,
                "active": d.recent_activity or [],
            }
            for d in rows.scalars().all()
        ]

    async def count(self, session: AsyncSession) -> int:
        rows = await session.execute(select(Device.id))
        return len(list(rows.scalars().all()))


device_manager = DeviceManager()
