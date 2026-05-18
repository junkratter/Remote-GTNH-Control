"""One-shot timer manager (APScheduler-backed)."""

from __future__ import annotations

import copy
import json
import uuid
from datetime import datetime, timedelta
from typing import Any

from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.date import DateTrigger
from fastapi import HTTPException

from app.automation.config import timer_config
from app.core.constants import COMPLETED, PENDING, READY
from app.core.logging import logger


class TimerManager:
    def __init__(self) -> None:
        self.scheduler = BackgroundScheduler(jobstores={"default": MemoryJobStore()})
        self.scheduler.start()
        self.timers: dict[str, dict[str, Any]] = {}

    def get_config_list(self) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for name, timer in timer_config.items():
            entry: dict[str, Any] = {
                "name": name,
                "description": timer.get("description"),
                "args": timer.get("args", []),
                "actions": [],
            }
            for action_id, action in timer.get("actions", {}).items():
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

    def _execute_action(self, action: dict[str, Any], kwargs: dict[str, Any]) -> Any:
        func = action.get("function")
        if not callable(func):
            raise ValueError("Action function is not callable")
        args_def = action.get("args", [])
        call_kwargs: dict[str, Any] = {}
        for arg in args_def:
            name = arg["field"]
            kind = arg.get("type")
            default = arg.get("default")
            value = kwargs.get(name, default)
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

    def _exec_timer(self, timer_id: str) -> None:
        config = self.timers[timer_id]
        try:
            config["result"] = self._execute_action(
                config["action"], config["action"]["action_kwargs"]
            )
        except Exception as exc:
            logger.exception("Timer %s failed", timer_id)
            config["result"] = {"error": str(exc)}
        finally:
            config["status"] = COMPLETED
            config["time"]["completed"] = datetime.utcnow().isoformat()
            config["running"] = False

    def register_timer(
        self,
        timer_name: str,
        action_name: str,
        timer_kwargs: dict[str, Any],
        action_kwargs: dict[str, Any],
    ) -> str:
        if timer_name == "delay_timer":
            run_date = datetime.now() + timedelta(seconds=int(timer_kwargs["delay"]))
        elif timer_name == "scheduled_timer":
            run_date = datetime.fromisoformat(timer_kwargs["time"])
        else:
            raise HTTPException(status_code=400, detail="Unsupported timer kind")

        if timer_name not in timer_config:
            raise HTTPException(status_code=404, detail=f"Timer '{timer_name}' not found")
        config = copy.deepcopy(timer_config[timer_name])
        if action_name not in config.get("actions", {}):
            raise HTTPException(status_code=404, detail=f"Action '{action_name}' not found")

        config["name"] = timer_name
        config["action"] = config["actions"][action_name]
        del config["actions"]
        config["kwargs"] = copy.deepcopy(timer_kwargs)
        config["action"]["action_kwargs"] = copy.deepcopy(action_kwargs)
        config["time"] = {
            "created": datetime.utcnow().isoformat(),
            "last_start": None,
            "excuted": run_date.isoformat(),
            "completed": None,
        }
        config["result"] = None
        config["status"] = READY
        config["running"] = False

        timer_id = str(uuid.uuid4())
        self.timers[timer_id] = config

        job = self.scheduler.add_job(
            self._exec_timer,
            DateTrigger(run_date=run_date),
            args=[timer_id],
            id=timer_id,
        )
        job.pause()
        return timer_id

    def unregister_timer(self, timer_id: str) -> None:
        if timer_id not in self.timers:
            return
        del self.timers[timer_id]
        job = self.scheduler.get_job(timer_id)
        if job:
            self.scheduler.remove_job(timer_id)

    def start(self, timer_id: str) -> None:
        if timer_id not in self.timers:
            raise HTTPException(status_code=404, detail=f"Timer '{timer_id}' not found")
        config = self.timers[timer_id]
        if config["running"]:
            raise HTTPException(status_code=400, detail="Timer already running")
        run_date = datetime.fromisoformat(config["time"]["excuted"])
        if run_date < datetime.now():
            raise HTTPException(status_code=400, detail="Timer already expired")
        job = self.scheduler.get_job(timer_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job missing in scheduler")
        job.resume()
        config["running"] = True
        config["status"] = PENDING
        config["time"]["last_start"] = datetime.utcnow().isoformat()

    def stop(self, timer_id: str, force: bool = False) -> None:
        if timer_id not in self.timers:
            return
        config = self.timers[timer_id]
        if not config["running"] and not force:
            return
        job = self.scheduler.get_job(timer_id)
        if job:
            job.pause()
        config["running"] = False
        config["status"] = READY

    def get_timer_list(self) -> dict[str, dict[str, Any]]:
        return self.timers

    def stop_all(self) -> None:
        for timer_id in list(self.timers.keys()):
            if self.timers[timer_id]["running"]:
                self.stop(timer_id, force=True)


timer_manager = TimerManager()
