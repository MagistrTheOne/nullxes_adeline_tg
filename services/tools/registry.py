"""OpenAI tool schemas + dispatch."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from services.tools.summaries import get_company_profile, get_daily_summary
from services.user_state import user_states

try:
    from zoneinfo import ZoneInfo

    MSK = ZoneInfo("Europe/Moscow")
except Exception:
    MSK = timezone(timedelta(hours=3), name="Europe/Moscow")

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "Текущие дата и время в Europe/Moscow.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_daily_summary",
            "description": (
                "Сводка NULLXES за конкретную календарную дату. "
                "Если available=false — сводки нет, не выдумывай."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Дата в формате YYYY-MM-DD",
                    }
                },
                "required": ["date"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_company_profile",
            "description": "Профиль NULLXES, продукты и роль Adeline Kalen.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_user_memory",
            "description": "Память/стейт пользователя: phase, intro, goals, tasks.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_user_memory",
            "description": (
                "Обновить память пользователя. "
                "После первого знакомства ставь intro_shown=true и phase=active."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "intro_shown": {"type": "boolean"},
                    "knows_nullxes": {"type": "boolean"},
                    "phase": {
                        "type": "string",
                        "enum": ["new", "onboarding", "active"],
                    },
                    "preferred_channel": {
                        "type": "string",
                        "enum": ["unknown", "text", "voice", "video"],
                    },
                    "goals": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Список целей пользователя (заменяет цели).",
                    },
                    "notes": {"type": "string"},
                    "append_goal": {
                        "type": "string",
                        "description": "Добавить одну цель, не затирая остальные.",
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Создать задачу/пункт плана для пользователя.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "due": {"type": "string", "description": "Опционально YYYY-MM-DD"},
                    "notes": {"type": "string"},
                },
                "required": ["title"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "Список задач пользователя.",
            "parameters": {
                "type": "object",
                "properties": {
                    "include_done": {"type": "boolean"},
                },
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_task",
            "description": "Обновить статус/текст задачи (open|done|cancelled).",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["open", "done", "cancelled"],
                    },
                    "title": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["task_id"],
                "additionalProperties": False,
            },
        },
    },
]


def _current_datetime() -> dict:
    now = datetime.now(MSK)
    return {
        "timezone": "Europe/Moscow",
        "iso": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "human_ru": now.strftime("%d.%m.%Y %H:%M"),
    }


async def execute_tool(
    name: str,
    arguments_json: str,
    *,
    user_id: int = 0,
) -> str:
    try:
        args = json.loads(arguments_json or "{}")
    except json.JSONDecodeError:
        args = {}

    if name == "get_current_datetime":
        result: Any = _current_datetime()
    elif name == "get_daily_summary":
        date = str(args.get("date") or "").strip()
        if not date:
            result = {"available": False, "message": "date is required (YYYY-MM-DD)"}
        else:
            result = get_daily_summary(date)
    elif name == "get_company_profile":
        result = get_company_profile()
    elif name == "get_user_memory":
        result = user_states.public_view(user_id)
    elif name == "update_user_memory":
        patch: dict[str, Any] = {}
        for key in (
            "intro_shown",
            "knows_nullxes",
            "phase",
            "preferred_channel",
            "notes",
            "goals",
        ):
            if key in args and args[key] is not None:
                patch[key] = args[key]
        if args.get("append_goal"):
            state = user_states.get(user_id)
            goals = list(state.get("goals") or [])
            goal = str(args["append_goal"]).strip()
            if goal and goal not in goals:
                goals.append(goal)
            patch["goals"] = goals
        if patch:
            user_states.patch(user_id, **patch)
        result = user_states.public_view(user_id)
    elif name == "create_task":
        title = str(args.get("title") or "").strip()
        if not title:
            result = {"error": "title required"}
        else:
            task = user_states.create_task(
                user_id,
                title=title,
                due=str(args.get("due") or ""),
                notes=str(args.get("notes") or ""),
            )
            result = {"ok": True, "task": task}
    elif name == "list_tasks":
        result = {
            "tasks": user_states.list_tasks(
                user_id, include_done=bool(args.get("include_done"))
            )
        }
    elif name == "update_task":
        task_id = str(args.get("task_id") or "").strip()
        updated = user_states.update_task(
            user_id,
            task_id,
            status=args.get("status"),
            title=args.get("title"),
            notes=args.get("notes"),
        )
        result = {"ok": bool(updated), "task": updated}
    else:
        result = {"error": f"Unknown tool: {name}"}

    return json.dumps(result, ensure_ascii=False)
