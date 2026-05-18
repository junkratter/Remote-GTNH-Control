"""Helpers for autocraft.

Pattern programming and craft requests are delivered to OC clients as
plain Lua commands fetched via the standard `/api/task/get` long-polling
endpoint. See `oc-client/plugins/ae.lua` for the runtime side.
"""

from __future__ import annotations

import json
import uuid
from typing import Any, Iterable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import READY
from app.core.tasks import task_store
from app.db.models import AutocraftPattern, AutocraftRequest


def _lua_table(value: Any) -> str:
    """Render a Python value as a Lua literal (limited subset)."""

    if value is None:
        return "nil"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"
    if isinstance(value, (list, tuple)):
        items = ", ".join(_lua_table(v) for v in value)
        return "{" + items + "}"
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            if isinstance(k, str) and k.isidentifier():
                parts.append(f"{k} = {_lua_table(v)}")
            else:
                parts.append(f"[{_lua_table(k)}] = {_lua_table(v)}")
        return "{" + ", ".join(parts) + "}"
    raise TypeError(f"Cannot render {type(value)!r} as Lua literal")


def build_pattern_commands(pattern: AutocraftPattern) -> list[str]:
    """Build Lua commands that program a single ME Interface slot.

    Emits TWO commands so we can show stage-by-stage progress in the queue:
    one to switch interfaces and one to push the pattern.
    """

    inputs = pattern.inputs or []
    outputs = pattern.outputs or []
    return [
        f"return ae.setMeInterfaceAddress('{pattern.interface_address}')",
        (
            "return ae.programPattern("
            f"{pattern.slot}, '{pattern.kind}', "
            f"{_lua_table(inputs)}, {_lua_table(outputs)})"
        ),
    ]


def build_request_command(req: AutocraftRequest) -> str:
    cpu = f"'{req.cpu_name}'" if req.cpu_name else "nil"
    label = f"'{req.label}'" if req.label else "nil"
    name = req.item_name.replace("'", "\\'")
    return (
        f"return ae.requestItem('{name}', {req.item_damage}, "
        f"{req.amount}, {cpu}, {label})"
    )


def build_cpu_list_command(detail: bool = False) -> str:
    return f"return ae.getCpuList({'true' if detail else 'false'})"


def build_cancel_command(cpu_name: str) -> str:
    safe = cpu_name.replace("'", "\\'")
    return f"return ae.cancelCraftingByCpuName('{safe}')"


async def enqueue_craft(session: AsyncSession, request: AutocraftRequest) -> str:
    task_id = f"craft_{uuid.uuid4().hex[:12]}"
    command = build_request_command(request)
    await task_store.add(
        session,
        task_id=task_id,
        client_id=request.client_id,
        commands=[command],
        status=READY,
    )
    request.task_id = task_id
    request.state = "queued"
    await session.commit()
    return task_id


async def enqueue_cancel(session: AsyncSession, request: AutocraftRequest) -> str | None:
    """Best-effort cancel: schedules `ae.cancelCraftingByCpuName(cpu_name)`."""

    if not request.cpu_name:
        return None
    task_id = f"cancel_{uuid.uuid4().hex[:12]}"
    await task_store.add(
        session,
        task_id=task_id,
        client_id=request.client_id,
        commands=[build_cancel_command(request.cpu_name)],
        status=READY,
    )
    request.state = "cancelling"
    await session.commit()
    return task_id


async def enqueue_cpu_scan(
    session: AsyncSession,
    client_id: str,
    detail: bool = False,
) -> str:
    task_id = f"cpus_{uuid.uuid4().hex[:12]}"
    await task_store.add(
        session,
        task_id=task_id,
        client_id=client_id,
        commands=[build_cpu_list_command(detail=detail)],
        status=READY,
    )
    return task_id


def _parse_oc_command_result(raw: Any) -> dict[str, Any] | None:
    """Decode one executor result cell (JSON string or already a dict)."""

    if raw is None:
        return None
    if isinstance(raw, dict):
        return raw
    if isinstance(raw, str):
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"message": "invalid_json", "raw": raw[:500]}
    return None


def infer_craft_request_outcome(results: Any) -> tuple[str, dict[str, Any]]:
    """Map OC `/api/task/report` ``results`` list to ``(state, result_blob)``.

    ``state`` is ``done`` or ``failed``. See ``ae.requestItem`` return shape in
    ``oc-client/plugins/ae.lua``.
    """

    if not isinstance(results, list) or not results:
        return "failed", {"reason": "empty_results"}

    parsed: dict[str, Any] | None = None
    for raw in results:
        parsed = _parse_oc_command_result(raw)
        if parsed is not None:
            break

    if parsed is None:
        return "failed", {"reason": "no_parseable_results", "raw": results}

    msg = parsed.get("message")
    if msg != "success":
        return "failed", {"oc_message": msg, "payload": parsed}

    data = parsed.get("data")
    if not isinstance(data, dict):
        return "done", {"payload": parsed}

    if data.get("failed"):
        return "failed", {"oc": "craft_failed", **data}
    canceled = data.get("canceled") or {}
    if isinstance(canceled, dict) and canceled.get("result"):
        return "failed", {"oc": "canceled", **data}

    return "done", data


async def sync_craft_request_after_report(
    session: AsyncSession,
    task_id: str,
    results: Any,
) -> None:
    """When an OC client finishes a ``craft_*`` task, mirror outcome into DB."""

    if not task_id.startswith("craft_"):
        return

    stmt = select(AutocraftRequest).where(AutocraftRequest.task_id == task_id)
    row = (await session.execute(stmt)).scalar_one_or_none()
    if row is None:
        return
    if row.state == "cancelling":
        # A cancel task may still be in flight; avoid clobbering with a late craft report.
        return

    state, blob = infer_craft_request_outcome(results)
    row.state = state
    row.result = blob
    await session.commit()
