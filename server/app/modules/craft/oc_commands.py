"""Lua snippets for bulk ME interface programming."""

from __future__ import annotations

from typing import Any

from app.modules.autocraft.service import _lua_table


def bulk_program_lua(patterns: list[dict[str, Any]]) -> str:
    """Render a single OC task body chaining interface switches + ``programPattern``."""

    lines: list[str] = [
        "return (function()",
        "  local r = { message = 'success', data = {} }",
    ]
    for i, p in enumerate(patterns):
        iface = p.get("iface") or p.get("interface_address")
        if not iface:
            raise ValueError(f"pattern[{i}] missing iface")
        slot = int(p.get("slot", 0))
        kind = str(p.get("kind", "processing"))
        inputs = p.get("inputs") or []
        outputs = p.get("outputs") or []
        lines.append(f"  do local _ = ae.setMeInterfaceAddress({_lua_table(iface)})")
        lines.append("    if _.message ~= 'success' then return _ end")
        lines.append("  end")
        lines.append(
            f"  do local _ = ae.programPattern({int(slot)}, {_lua_table(kind)}, "
            f"{_lua_table(inputs)}, {_lua_table(outputs)})"
        )
        lines.append("    if _.message ~= 'success' then return _ end")
        lines.append("  end")
    lines.append("  return r")
    lines.append("end)()")
    return "\n".join(lines)
