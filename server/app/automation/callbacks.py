"""Result handlers / callbacks invoked when a task completes."""

from __future__ import annotations

import json
import re
from typing import Any


def echo(result: list[Any]) -> list[Any]:
    print(result)
    return result


def parse_capacitor_data(result: list[str]) -> dict[str, int]:
    """Parse Lapotron Capacitor Bank output into structured numbers."""

    payload = json.loads(result[0])
    extract = lambda x: int(re.sub(r"[^0-9]", "", x))

    capacitor: dict[str, str] = {}
    for item in payload:
        if ":" not in item:
            continue
        key, value = item.split(":", 1)
        if (key in {"EU Stored", "Total wireless EU"}) and "^" in value:
            continue
        capacitor[key] = value

    eu_stored = extract(capacitor.get("EU Stored", "0").replace(",", ""))
    total_wireless = extract(capacitor.get("Total wireless EU", "0").replace(",", ""))
    return {"eu_stored": eu_stored, "total_wireless_eu": total_wireless}


def check_cpu_free(result: list[str]) -> bool:
    """Return True when AE2 CPU is idle (`busy == false`)."""

    cpu_status = json.loads(result[0]).get("data", {})
    return cpu_status.get("busy") is False
