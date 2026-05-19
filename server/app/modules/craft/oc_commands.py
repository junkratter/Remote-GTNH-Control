"""Lua snippets for bulk ME interface programming."""

from __future__ import annotations

from typing import Any

from app.modules.autocraft.service import _lua_table


def bulk_program_lua(patterns: list[dict[str, Any]]) -> str:
    """Single OC chunk delegating to ``ae.bulkProgramPatterns`` (see ``ae_patterns.lua``)."""

    return f"return ae.bulkProgramPatterns({_lua_table(patterns)})"
