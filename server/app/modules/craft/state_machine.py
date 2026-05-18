"""Allowed ``craft_jobs.state`` transitions (ADR-006)."""

from __future__ import annotations

_ALLOWED: dict[str, frozenset[str]] = {
    "planning": frozenset({"awaiting_choice", "ready", "failed", "cancelled"}),
    "awaiting_choice": frozenset({"ready", "failed", "cancelled"}),
    "ready": frozenset({"programmed", "failed", "cancelled"}),
    "programmed": frozenset({"crafting", "done", "failed", "cancelled"}),
    "crafting": frozenset({"done", "failed", "cancelled"}),
    "done": frozenset(),
    "failed": frozenset(),
    "cancelled": frozenset(),
}


def assert_transition_ok(current: str, new: str) -> None:
    if current == new:
        return
    nxt = _ALLOWED.get(current)
    if nxt is None or new not in nxt:
        raise ValueError(f"Invalid craft job transition: {current!r} -> {new!r}")
