"""/api/automate/* — triggers + timers."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends

from app.automation.config import action_template
from app.core.auth import token_required
from app.core.timers import timer_manager
from app.core.triggers import trigger_manager
from app.schemas import (
    AddTimerModel,
    AddTriggerModel,
    StandardResponseModel,
    TimerRequestModel,
    TriggerRequestModel,
)


router = APIRouter(dependencies=[Depends(token_required)])


@router.get("/trigger/config", response_model=StandardResponseModel)
async def get_trigger_config() -> dict:
    return {"code": 200, "message": "success", "data": trigger_manager.get_config_list()}


@router.post("/trigger/add", response_model=StandardResponseModel)
async def add_trigger(trigger: AddTriggerModel) -> dict:
    trigger_task_id = trigger_manager.register_trigger(
        trigger.name,
        trigger.action,
        trigger.trigger_kwargs,
        trigger.action_kwargs,
        trigger.interval,
    )
    return {"code": 200, "message": "success", "data": {"trigger_task_id": trigger_task_id}}


@router.post("/trigger/remove", response_model=StandardResponseModel)
async def remove_trigger(trigger: TriggerRequestModel) -> dict:
    trigger_manager.unregister_trigger(trigger.trigger_task_id)
    return {"code": 200, "message": "success"}


@router.get("/trigger/list", response_model=StandardResponseModel)
async def get_trigger_list() -> dict:
    triggers = trigger_manager.get_trigger_list()
    sanitised = json.loads(json.dumps(triggers, default=lambda x: None))
    return {"code": 200, "message": "success", "data": sanitised}


@router.post("/trigger/start", response_model=StandardResponseModel)
async def start_trigger(trigger: TriggerRequestModel) -> dict:
    trigger_manager.start(trigger.trigger_task_id)
    return {"code": 200, "message": "success"}


@router.post("/trigger/stop", response_model=StandardResponseModel)
async def stop_trigger(trigger: TriggerRequestModel) -> dict:
    trigger_manager.stop(trigger.trigger_task_id)
    return {"code": 200, "message": "success"}


@router.get("/timer/config", response_model=StandardResponseModel)
async def get_timer_config() -> dict:
    return {"code": 200, "message": "success", "data": timer_manager.get_config_list()}


@router.post("/timer/add", response_model=StandardResponseModel)
async def add_timer(timer: AddTimerModel) -> dict:
    timer_id = timer_manager.register_timer(
        timer.name, timer.action, timer.trigger_kwargs, timer.action_kwargs
    )
    return {"code": 200, "message": "success", "data": {"timer_id": timer_id}}


@router.post("/timer/remove", response_model=StandardResponseModel)
async def remove_timer(timer: TimerRequestModel) -> dict:
    timer_manager.unregister_timer(timer.timer_id)
    return {"code": 200, "message": "success"}


@router.get("/timer/list", response_model=StandardResponseModel)
async def get_timer_list() -> dict:
    timers = timer_manager.get_timer_list()
    sanitised = json.loads(json.dumps(timers, default=lambda x: None))
    return {"code": 200, "message": "success", "data": sanitised}


@router.post("/timer/start", response_model=StandardResponseModel)
async def start_timer(timer: TimerRequestModel) -> dict:
    timer_manager.start(timer.timer_id)
    return {"code": 200, "message": "success"}


@router.post("/timer/stop", response_model=StandardResponseModel)
async def stop_timer(timer: TimerRequestModel) -> dict:
    timer_manager.stop(timer.timer_id)
    return {"code": 200, "message": "success"}


@router.get("/action/template", response_model=StandardResponseModel)
async def get_action_template() -> dict:
    return {"code": 200, "message": "success", "data": action_template}
