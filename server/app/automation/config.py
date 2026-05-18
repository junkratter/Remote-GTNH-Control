"""Static automation configuration.

Mirrors the original `config.py`: declarative dictionaries describing the
named tasks, timer tasks, triggers and actions. Edit here to add new OC
commands that can be triggered from the UI / scheduler.

> NOTE: business / functional handlers live in `app/automation/actions.py`
> and `app/automation/callbacks.py`.
"""

from __future__ import annotations

from app.automation import actions, callbacks


# ---------------------------------------------------------------------------
# Timer tasks (periodic OC commands)
# ---------------------------------------------------------------------------

timer_task_config: dict[str, dict] = {
    # Example (disabled by default):
    # "monitor": {
    #     "interval": 300,
    #     "client_id": "client_01",
    #     "commands": ["return getCapacitorInfo()"],
    #     "cache": True,
    #     "handle": callbacks.parse_capacitor_data,
    #     "callback": None,
    #     "save_history": True,
    #     "history_days": 7,
    # },
}


# ---------------------------------------------------------------------------
# Named tasks (triggered manually via POST /api/task/task)
# ---------------------------------------------------------------------------

task_config: dict[str, dict] = {
    "getCpuDetailList": {
        "client_id": "client_01",
        "commands": ["return ae.getCpuList(true)"],
        "cache": True,
    },
    "getCpuList": {
        "client_id": "client_01",
        "commands": ["return ae.getCpuList()"],
        "cache": True,
    },
    "getAllItems": {
        "client_id": "client_01",
        "commands": ["return ae.getAllItems()"],
        "cache": True,
        "chunked": True,
    },
    "getAllSilempleItems": {
        "client_id": "client_01",
        "commands": ["return ae.getAllSilempleItems()"],
        "cache": True,
        "chunked": True,
    },
    "getAllCraftables": {
        "client_id": "client_01",
        "commands": ["return ae.getAllCraftables()"],
        "cache": True,
    },
    "getAllCraftablesAndCpus": {
        "client_id": "client_01",
        "commands": [
            "return ae.getAllCraftables()",
            "return ae.getCpuList()",
        ],
        "cache": True,
    },
}


# ---------------------------------------------------------------------------
# Trigger config (conditional automation)
# ---------------------------------------------------------------------------

trigger_config: dict[str, dict] = {
    "cpu_idle": {
        "interval": 180,
        "description": "When the specified CPU becomes idle",
        "task": {
            "task_id": None,
            "client_id": "{client_id}",
            "commands": ["return ae.getCpuInfoByName('{cpu_name}')"],
            "handle": callbacks.check_cpu_free,
        },
        "args": [
            {
                "key": "client_id",
                "field": "client_id",
                "type": "str",
                "default": "",
                "description": "Client id of the OC computer.",
            },
            {
                "key": "cpu_name",
                "field": "cpu_name",
                "type": "str",
                "description": "AE Crafting CPU name.",
            },
        ],
        "actions": {
            "craft": {
                "name": "Craft item",
                "description": "Sends a craft request to OC.",
                "function": actions.craft_item,
                "args": [
                    {"field": "client_id", "type": "str", "default": ""},
                    {"field": "item_name", "type": "str"},
                    {"field": "item_damage", "type": "int"},
                    {"field": "item_amount", "type": "int", "default": 1},
                    {"field": "cpu_name", "type": "str", "default": None},
                    {"field": "label", "type": "str", "default": None},
                ],
            },
            "http_request": {
                "name": "Send HTTP request",
                "description": "POSTs a payload to an arbitrary URL.",
                "function": actions.send_http_request,
                "args": [
                    {"field": "method", "type": "str", "default": "GET"},
                    {"field": "url", "type": "str"},
                    {"field": "headers", "type": "str", "default": None},
                    {"field": "params", "type": "dict", "default": None},
                    {"field": "data", "type": "dict", "default": None},
                ],
            },
        },
    },
}


# ---------------------------------------------------------------------------
# Timer (one-shot scheduled actions)
# ---------------------------------------------------------------------------

_craft_action_template = {
    "name": "Craft item",
    "description": "Sends a craft request to OC.",
    "function": actions.craft_item,
    "args": [
        {"field": "client_id", "type": "str", "default": ""},
        {"field": "item_name", "type": "str"},
        {"field": "item_damage", "type": "int"},
        {"field": "item_amount", "type": "int", "default": 1},
        {"field": "cpu_name", "type": "str", "default": None},
        {"field": "label", "type": "str", "default": None},
    ],
}


timer_config: dict[str, dict] = {
    "delay_timer": {
        "description": "Run after N seconds.",
        "args": [
            {"key": "delay", "field": "delay", "type": "int", "description": "Delay seconds"},
        ],
        "actions": {"craft": _craft_action_template},
    },
    "scheduled_timer": {
        "description": "Run at the specified ISO datetime.",
        "args": [
            {"key": "time", "field": "time", "type": "str", "description": "ISO timestamp"},
        ],
        "actions": {"craft": _craft_action_template},
    },
}


action_template: dict[str, dict] = {
    "cpu_idle": {
        "http_request": [
            {
                "name": "OneBot v11 group message",
                "description": "Notify a QQ group when CPU is idle.",
                "action_kwargs": {
                    "method": "POST",
                    "url": "http://<ONEBOT_SERVER_ADDRESS>/send_group_msg",
                    "headers": {"Authorization": "<ONEBOT_SERVER_TOKEN>"},
                    "data": '{"group_id": "<TARGET_GROUP_ID>","message": "CPU \'<CPU_NAME>\' is idle"}',
                },
                "args": {"key_values": ["headers"]},
            },
        ]
    }
}
