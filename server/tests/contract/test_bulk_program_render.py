"""Lua bulk pattern command matches OC plugin expectations."""

from __future__ import annotations

from app.modules.craft.oc_commands import bulk_program_lua


def test_bulk_program_lua_escapes_iface_and_emits_do_blocks():
    lua = bulk_program_lua(
        [
            {
                "interface_address": "a'b\\x",
                "slot": 3,
                "kind": "processing",
                "inputs": [{"name": "ingotIron", "damage": 0, "amount": 1}],
                "outputs": [],
            }
        ]
    )
    assert "ae.setMeInterfaceAddress('a\\'b\\\\x')" in lua
    assert "ae.programPattern(3," in lua
