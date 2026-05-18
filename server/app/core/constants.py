"""Domain-wide constants (task / robot states).

Plain string namespaces (instead of `enum.StrEnum`) so the module works
on both Python 3.10 (dev) and 3.11+ (prod).
"""

from __future__ import annotations


READY = "ready"
PENDING = "pending"
UPLOADING = "uploading"
COMPLETED = "completed"


TASK_STATUSES = (READY, PENDING, UPLOADING, COMPLETED)


class RobotState:
    IDLE: str = "idle"
    MOVING: str = "moving"
    WORKING: str = "working"
    UNLOADING: str = "unloading"
    RETURNING: str = "returning"
    ERROR: str = "error"


class MiningJobState:
    PENDING: str = "pending"
    RUNNING: str = "running"
    UNLOADING: str = "unloading"
    DONE: str = "done"
    FAILED: str = "failed"


class PowerJobState:
    PENDING: str = "pending"
    RUNNING: str = "running"
    DONE: str = "done"
    FAILED: str = "failed"


class RobotKind:
    CROP: str = "crop"
    MINER: str = "miner"
    POWER: str = "power"
    SCANNER: str = "scanner"
    GENERIC: str = "generic"
