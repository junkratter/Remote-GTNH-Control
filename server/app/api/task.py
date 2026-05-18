"""/api/task/* — long-poll contract for OC clients.

**DO NOT** change response shapes (`code/message/data`, `taskId`, `commands`,
`is_chunked`) without:

1. Updating `oc-client/src/executor.lua`.
2. Updating `kb/01-architecture/api-contract.md`.
3. Adding a contract regression in `tests/contract/test_task_contract.py`.
"""

from __future__ import annotations

import base64
import gzip
import json
import re
import uuid
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.automation.config import task_config, timer_task_config
from app.core.auth import token_required
from app.core.constants import COMPLETED, PENDING, READY, UPLOADING
from app.core.devices import device_manager
from app.core.encoding import decode_request_body
from app.core.logging import logger
from app.core.tasks import _to_dict, task_store
from app.core.triggers import trigger_manager
from app.db.session import get_session
from app.modules.autocraft import service as autocraft_service
from app.schemas import (
    AddCommandModel,
    AddTaskByNameModel,
    CommandChunkedResultModel,
    CommandResultModel,
    StandardResponseModel,
)


router = APIRouter(dependencies=[Depends(token_required)])


@router.get("/get", response_model=StandardResponseModel)
async def get_commands(
    x_client_id: str | None = Header(None, alias="X-Client-ID"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Return the next READY task for the (optional) client_id."""

    await device_manager.record(session, x_client_id, "get")
    task = await task_store.claim_next(session, client_id=x_client_id)
    if task is None:
        return {"code": 200, "message": "No ready commands available", "data": None}
    return {
        "code": 200,
        "message": "Commands for task fetched successfully",
        "data": {
            "taskId": task.id,
            "commands": list(task.commands or []),
            "is_chunked": task.chunked,
        },
    }


async def _read_oc_payload(request: Request, model_cls) -> Any:
    body = await request.body()
    try:
        text = decode_request_body(body)
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.error("JSON decode failed: %s", exc)
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc
    return model_cls(**payload)


def _is_ae_item_row(entry: Any) -> bool:
    return isinstance(entry, dict) and ("name" in entry or "label" in entry)


def _flatten_chunked_items(results: Any) -> list[Any]:
    """Flatten chunked getAllItems payloads (item dicts or nested full arrays per chunk)."""

    if results is None:
        return []
    if not isinstance(results, list):
        return [results] if _is_ae_item_row(results) else []

    flat: list[Any] = []
    for entry in results:
        if isinstance(entry, dict):
            flat.append(entry)
            continue
        if isinstance(entry, list):
            if not entry:
                continue
            if _is_ae_item_row(entry[0]):
                flat.extend(entry)
            else:
                flat.extend(_flatten_chunked_items(entry))
            continue
        if isinstance(entry, str):
            try:
                parsed = json.loads(entry)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and parsed.get("message") == "success":
                data = parsed.get("data")
                if isinstance(data, list):
                    flat.extend(_flatten_chunked_items(data))
            elif isinstance(parsed, list):
                flat.extend(_flatten_chunked_items(parsed))
    return flat


def _dedupe_ae_items(flat: list[Any]) -> list[Any]:
    """AE returns one row per stack type; drop duplicate rows from chunked merge bugs."""

    by_key: dict[tuple, dict] = {}
    for row in flat:
        if not _is_ae_item_row(row):
            continue
        key = (row.get("name"), row.get("damage"), row.get("label"))
        prev = by_key.get(key)
        if prev is None or (row.get("size") or 0) > (prev.get("size") or 0):
            by_key[key] = row
    return list(by_key.values())


def _merge_chunked_results(
    existing: Any, new_chunk: Any, *, replace: bool, dedupe: bool = False
) -> list[Any]:
    if replace:
        merged = _flatten_chunked_items(new_chunk)
    else:
        merged = _flatten_chunked_items(existing)
        merged.extend(_flatten_chunked_items(new_chunk))
    return _dedupe_ae_items(merged) if dedupe else merged


def _run_handle_and_callback(task_id: str, results: Any) -> Any:
    """Run optional handle/callback defined in automation config."""

    new_results = results
    for source in (timer_task_config, task_config, trigger_manager.get_tasks()):
        entry = source.get(task_id)
        if not entry:
            continue
        handle = entry.get("handle")
        if callable(handle):
            try:
                new_results = handle(new_results)
            except Exception:
                logger.exception("handle() raised for task %s", task_id)
        callback = entry.get("callback")
        if callable(callback):
            try:
                callback(new_results)
            except Exception:
                logger.exception("callback() raised for task %s", task_id)
    return new_results


def _maybe_save_history(task_id: str, results: Any) -> None:
    from app.core.tasks import sync_task_manager

    for source in (timer_task_config, task_config):
        entry = source.get(task_id)
        if not entry or not entry.get("save_history"):
            continue
        days = int(entry.get("history_days", 7))
        try:
            sync_task_manager.save_to_history(task_id, results, days)
        except Exception:
            logger.exception("history save failed for %s", task_id)


@router.post("/chunked_report", response_model=StandardResponseModel)
async def receive_chunked_report(
    request: Request,
    chunked: int = Query(-1, description="1=start, >1=middle, 0=final"),
    x_client_id: str | None = Header(None, alias="X-Client-ID"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    command_result: CommandChunkedResultModel = await _read_oc_payload(
        request, CommandChunkedResultModel
    )
    task_id = command_result.task_id
    results = command_result.results

    task = await task_store.get(session, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    dedupe_items = task_id in ("getAllItems", "getAllSilempleItems")

    if chunked == 1:
        merged = _merge_chunked_results(
            None, results, replace=True, dedupe=dedupe_items
        )
        await task_store.update(session, task_id, status=UPLOADING, results=merged)
        return {
            "code": 200,
            "message": "Chunked data for task received and reset successfully",
            "data": {"taskId": task_id},
        }

    if chunked > 1:
        if task.status != UPLOADING:
            return {
                "code": 200,
                "message": "Task status is not uploading",
                "data": {"taskId": task_id},
            }
        merged = _merge_chunked_results(
            task.results, results, replace=False, dedupe=dedupe_items
        )
        await task_store.update(session, task_id, status=UPLOADING, results=merged)
        return {
            "code": 200,
            "message": "Chunked data for task added successfully",
            "data": {"taskId": task_id},
        }

    if chunked == 0:
        await device_manager.record(session, x_client_id, "chunked_report")
        final_results = _merge_chunked_results(
            task.results, results, replace=False, dedupe=dedupe_items
        )
        final_results = _run_handle_and_callback(task_id, final_results)
        await task_store.update(session, task_id, status=COMPLETED, results=final_results)
        await autocraft_service.sync_craft_request_after_report(session, task_id, final_results)
        _maybe_save_history(task_id, final_results)
        return {
            "code": 200,
            "message": "Task result received and completed",
            "data": {"taskId": task_id},
        }

    raise HTTPException(status_code=400, detail="Invalid value for `chunked`")


@router.post("/report", response_model=StandardResponseModel)
async def receive_report(
    request: Request,
    x_client_id: str | None = Header(None, alias="X-Client-ID"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    command_result: CommandResultModel = await _read_oc_payload(request, CommandResultModel)
    await device_manager.record(session, x_client_id, "report")
    task_id = command_result.task_id
    results = command_result.results

    if not await task_store.exists(session, task_id):
        raise HTTPException(status_code=404, detail="Task not found")

    final_results = _run_handle_and_callback(task_id, results)
    await task_store.update(session, task_id, status=COMPLETED, results=final_results)
    await autocraft_service.sync_craft_request_after_report(session, task_id, final_results)
    _maybe_save_history(task_id, final_results)
    return {"code": 200, "message": "Task result received", "data": {"taskId": task_id}}


@router.post("/add", response_model=StandardResponseModel)
async def add_command(
    data: AddCommandModel,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    task_id = data.task_id or str(uuid.uuid4())
    if not re.match(r"^[a-zA-Z0-9_-]+$", task_id):
        return {"code": 400, "message": "Invalid taskId format", "data": None}
    if not data.commands:
        return {"code": 400, "message": "No commands provided or invalid format", "data": None}

    await task_store.add(session, task_id, data.client_id, data.commands, READY)
    return {
        "code": 200,
        "message": f"Task added with {len(data.commands)} command(s)",
        "data": {"taskId": task_id},
    }


@router.get("/status", response_model=StandardResponseModel)
async def get_task_status(
    task_id: str = Query(..., description="Task id"),
    remove: bool = Query(True, description="Delete a COMPLETED ad-hoc task afterwards"),
    use_gzip: bool = Query(False, description="Return base64(gzip(result))"),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    task = await task_store.get(session, task_id)
    if task is None:
        return {"code": 404, "message": "Task not found", "data": None}

    if task.status == COMPLETED and remove:
        if task_id not in timer_task_config and task_id not in task_config:
            await task_store.remove(session, task_id)

    payload = _to_dict(task)
    result = payload.get("results")
    if use_gzip and result is not None:
        gz = gzip.compress(json.dumps(result).encode(), compresslevel=6)
        result = base64.b64encode(gz).decode()

    return {
        "code": 200,
        "message": "success",
        "data": {
            "gzip": use_gzip,
            "taskId": task_id,
            "status": payload["status"],
            "result": result,
            "created_time": payload["created_time"],
            "pending_time": payload["pending_time"],
            "completed_time": payload["completed_time"],
        },
    }


@router.post("/task", response_model=StandardResponseModel)
async def add_task_by_name(
    data: AddTaskByNameModel,
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    task_id = data.task_id
    entry = task_config.get(task_id)
    if not entry:
        return {
            "code": 404,
            "message": f"Task config not found for task name: {task_id}",
            "data": {"taskId": task_id},
        }
    commands = entry.get("commands") or []
    if not commands:
        return {
            "code": 400,
            "message": f"No commands found for task name: {task_id}",
            "data": {"taskId": task_id},
        }
    is_chunked = bool(entry.get("chunked", False))
    cache = bool(entry.get("cache", False))
    client_id = data.client_id or entry.get("client_id")

    if cache:
        ok = await task_store.update(session, task_id, status=READY)
        if not ok:
            await task_store.add(
                session, task_id, client_id, commands, READY, is_chunked=is_chunked
            )
    else:
        await task_store.add(session, task_id, client_id, commands, READY, is_chunked=is_chunked)

    return {
        "code": 200,
        "message": f"Task added with {len(commands)} command(s)",
        "data": {"taskId": task_id},
    }


@router.get("/history", response_model=StandardResponseModel)
async def get_task_history(
    task_id: str = Query(...),
    start_time: int | None = Query(None),
    end_time: int | None = Query(None),
    use_gzip: bool = Query(False),
    session: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    history = await task_store.history(session, task_id, start_time, end_time)
    if history is None:
        return {"code": 404, "message": "Task not found", "data": None}

    payload = {"taskId": task_id, "total": len(history), "history": history}
    if use_gzip:
        gz = gzip.compress(json.dumps(payload).encode(), compresslevel=6)
        return {
            "code": 200,
            "message": "success",
            "data": {"gzip": True, "result": base64.b64encode(gz).decode()},
        }
    return {"code": 200, "message": "success", "data": payload}
