"""Trigger manager — periodically polls task results and runs actions."""

from __future__ import annotations

import copy
import json
import os
import threading
import uuid
from datetime import datetime
from typing import Any

from fastapi import HTTPException

from app.automation.config import trigger_config
from app.core.constants import COMPLETED, PENDING, READY
from app.core.logging import logger
from app.core.tasks import sync_task_manager


class TriggerManager:
    def __init__(self) -> None:
        self.triggers: dict[str, dict[str, Any]] = {}

    def get_config_list(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for trigger_name, trigger in trigger_config.items():
            entry: dict[str, Any] = {
                "name": trigger_name,
                "description": trigger.get("description"),
                "args": trigger.get("args", []),
                "actions": [],
            }
            for action_id, action in trigger.get("actions", {}).items():
                entry["actions"].append(
                    {
                        "id": action_id,
                        "name": action.get("name"),
                        "description": action.get("description"),
                        "args": action.get("args", []),
                    }
                )
            out.append(entry)
        return out

    def get_tasks(self) -> dict[str, dict[str, Any]]:
        tasks: dict[str, dict[str, Any]] = {}
        for trigger in self.triggers.values():
            task_id = trigger.get("task", {}).get("task_id")
            if task_id:
                tasks[task_id] = trigger.get("task", {})
        return tasks

    @staticmethod
    def _replace_placeholders(obj: Any, params: dict[str, Any]) -> Any:
        if isinstance(obj, dict):
            return {k: TriggerManager._replace_placeholders(v, params) for k, v in obj.items()}
        if isinstance(obj, list):
            return [TriggerManager._replace_placeholders(v, params) for v in obj]
        if isinstance(obj, str):
            return obj.format(**params)
        return obj

    @staticmethod
    def _replace_angle_placeholders(obj: Any, params: dict[str, Any]) -> Any:
        if isinstance(obj, dict):
            return {
                k: TriggerManager._replace_angle_placeholders(v, params) for k, v in obj.items()
            }
        if isinstance(obj, list):
            return [TriggerManager._replace_angle_placeholders(v, params) for v in obj]
        if isinstance(obj, str):
            result = obj
            for key, value in params.items():
                if not isinstance(value, str):
                    continue
                result = result.replace(f"<{key.upper()}>", value)
            return result
        return obj

    def _execute_action(self, action: dict[str, Any], action_kwargs: dict[str, Any]) -> Any:
        func = action.get("function")
        if not callable(func):
            raise ValueError("Action function is not callable")
        args_def = action.get("args", [])
        call_kwargs: dict[str, Any] = {}
        for arg in args_def:
            name = arg["field"]
            kind = arg.get("type")
            default = arg.get("default")
            value = action_kwargs.get(name, default)
            if isinstance(value, str):
                if kind == "int":
                    value = int(value)
                elif kind == "float":
                    value = float(value)
                elif kind == "bool":
                    value = value.lower() == "true"
                elif kind in {"dict", "list"}:
                    value = json.loads(value)
                elif kind == "str":
                    value = str(value)
            call_kwargs[name] = value
        return func(**call_kwargs)

    def register_trigger(
        self,
        trigger_name: str,
        action_name: str,
        trigger_kwargs: dict[str, Any],
        action_kwargs: dict[str, Any],
        interval: int | None = None,
    ) -> str:
        if trigger_name not in trigger_config:
            raise HTTPException(status_code=404, detail=f"Trigger '{trigger_name}' not found")
        config = copy.deepcopy(trigger_config[trigger_name])
        if action_name not in config.get("actions", {}):
            raise HTTPException(status_code=404, detail=f"Action '{action_name}' not found")

        config["name"] = trigger_name
        if interval is not None:
            config["interval"] = interval
        config["action"] = config["actions"][action_name]
        del config["actions"]
        config["task"] = self._replace_placeholders(
            copy.deepcopy(config["task"]), trigger_kwargs
        )
        config["kwargs"] = copy.deepcopy(trigger_kwargs)
        config["action"]["action_kwargs"] = copy.deepcopy(action_kwargs)
        config["time"] = {
            "created": datetime.utcnow().isoformat(),
            "last_start": None,
            "last_monitor": None,
            "completed": None,
        }
        config["result"] = None
        config["status"] = READY
        config["running"] = False
        config["timer"] = None
        trigger_task_id = str(uuid.uuid4())
        self.triggers[trigger_task_id] = config
        logger.debug("Trigger '%s' registered", trigger_task_id)
        return trigger_task_id

    def unregister_trigger(self, trigger_task_id: str) -> None:
        if trigger_task_id not in self.triggers:
            return
        self.stop(trigger_task_id, force=True)
        del self.triggers[trigger_task_id]

    def _enqueue_task(self, task: dict[str, Any]) -> None:
        try:
            sync_task_manager.add_task(
                task_id=task["task_id"],
                client_id=task.get("client_id"),
                commands=task.get("commands", []),
                status=READY,
            )
        except Exception:
            logger.exception("Failed to enqueue trigger task")

    def _monitor(self, trigger_task_id: str) -> None:
        if trigger_task_id not in self.triggers:
            return
        config = self.triggers[trigger_task_id]
        if not config["running"]:
            return
        try:
            config["time"]["last_monitor"] = datetime.utcnow().isoformat()
            task_id = config.get("task", {}).get("task_id")
            if not task_id:
                task_id = str(uuid.uuid4())
                config["task"]["task_id"] = task_id
            status = sync_task_manager.get_task(task_id)

            if status:
                if status.get("status") == COMPLETED:
                    if status.get("results") is True:
                        action = config["action"]
                        action_kwargs = self._replace_angle_placeholders(
                            action.get("action_kwargs", {}), config.get("kwargs", {})
                        )
                        action_kwargs = self._replace_angle_placeholders(
                            action_kwargs, dict(os.environ)
                        )
                        config["result"] = {
                            "success": True,
                            "data": self._execute_action(action, action_kwargs),
                        }
                        config["status"] = COMPLETED
                        config["time"]["completed"] = datetime.utcnow().isoformat()
                        self.stop(trigger_task_id, is_completed=True)
                        return
                    self._enqueue_task(config["task"])
            else:
                self._enqueue_task(config["task"])

            timer = threading.Timer(
                config.get("interval", 180), self._monitor, args=(trigger_task_id,)
            )
            timer.start()
            config["timer"] = timer
        except Exception as exc:
            logger.exception("Trigger monitor failure")
            config["result"] = {"success": False, "error": str(exc)}
            self.stop(trigger_task_id)

    def start(self, trigger_task_id: str) -> None:
        if trigger_task_id not in self.triggers:
            raise HTTPException(status_code=404, detail=f"Trigger '{trigger_task_id}' not found")
        config = self.triggers[trigger_task_id]
        if config["running"]:
            raise HTTPException(status_code=400, detail="Trigger already running")
        config["running"] = True
        timer = threading.Timer(
            config.get("interval", 180), self._monitor, args=(trigger_task_id,)
        )
        timer.start()
        config["timer"] = timer
        config["status"] = PENDING
        config["time"]["last_start"] = datetime.utcnow().isoformat()

    def stop(
        self,
        trigger_task_id: str,
        force: bool = False,
        is_completed: bool = False,
    ) -> None:
        if trigger_task_id not in self.triggers:
            return
        config = self.triggers[trigger_task_id]
        if not config["running"] and not force:
            return
        config["running"] = False
        timer = config.get("timer")
        if timer is not None:
            timer.cancel()
        config["timer"] = None
        config["status"] = COMPLETED if is_completed else READY
        task_id = config.get("task", {}).get("task_id")
        if task_id:
            try:
                sync_task_manager.remove_task(task_id)
            except Exception:
                pass

    def get_trigger_list(self) -> dict[str, dict[str, Any]]:
        return self.triggers

    def stop_all(self) -> None:
        for trigger_task_id in list(self.triggers.keys()):
            if self.triggers[trigger_task_id]["running"]:
                self.stop(trigger_task_id, force=True)


trigger_manager = TriggerManager()
