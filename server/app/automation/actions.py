"""Action callables used by triggers/timers."""

from __future__ import annotations

import uuid
from typing import Any

import requests

from app.core.constants import READY
from app.core.tasks import sync_task_manager


def craft_item(
    client_id: str,
    item_name: str,
    item_damage: int,
    item_amount: int = 1,
    cpu_name: str | None = None,
    label: str | None = None,
) -> str:
    """Queue an `ae.requestItem(...)` task on the target OC client."""

    if cpu_name:
        if label:
            command = (
                f"return ae.requestItem('{item_name}', {item_damage}, "
                f"{item_amount}, '{cpu_name}', '{label}')"
            )
        else:
            command = (
                f"return ae.requestItem('{item_name}', {item_damage}, "
                f"{item_amount}, '{cpu_name}')"
            )
    else:
        if label:
            command = (
                f"return ae.requestItem('{item_name}', {item_damage}, "
                f"{item_amount}, nil, '{label}')"
            )
        else:
            command = f"return ae.requestItem('{item_name}', {item_damage}, {item_amount})"

    task_id = str(uuid.uuid4())
    sync_task_manager.add_task(
        task_id=task_id,
        client_id=client_id,
        commands=[command],
        status=READY,
        is_chunked=False,
    )
    return task_id


def send_http_request(
    method: str,
    url: str,
    headers: dict[str, str] | None = None,
    params: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
) -> str:
    """Generic HTTP shim usable as a trigger/timer action."""

    headers = headers or {}
    params = params or {}
    data = data or {}
    try:
        response = requests.request(
            method,
            url,
            headers=headers,
            params=params,
            json=data,
            timeout=5,
        )
        return response.text
    except requests.RequestException as exc:
        return str(exc)
