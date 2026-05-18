"""Craft job state machine guards (ADR-006)."""

import pytest

from app.modules.craft.state_machine import assert_transition_ok


def test_awaiting_choice_to_ready():
    assert_transition_ok("awaiting_choice", "ready")


def test_programmed_to_done():
    assert_transition_ok("programmed", "done")


def test_done_is_terminal():
    with pytest.raises(ValueError):
        assert_transition_ok("done", "ready")


def test_full_chain_planning_to_done_via_crafting():
    assert_transition_ok("planning", "awaiting_choice")
    assert_transition_ok("awaiting_choice", "ready")
    assert_transition_ok("ready", "programmed")
    assert_transition_ok("programmed", "crafting")
    assert_transition_ok("crafting", "done")


def test_planning_can_skip_to_ready_or_failed():
    assert_transition_ok("planning", "ready")
    assert_transition_ok("planning", "failed")


def test_programmed_can_finish_without_crafting_step():
    """OC may report completion directly from ``programmed`` (simplified path)."""

    assert_transition_ok("programmed", "done")


def test_invalid_skip_planning_to_programmed():
    with pytest.raises(ValueError):
        assert_transition_ok("planning", "programmed")


def test_invalid_ready_to_done():
    with pytest.raises(ValueError):
        assert_transition_ok("ready", "done")


def test_cancel_from_planning():
    assert_transition_ok("planning", "cancelled")
