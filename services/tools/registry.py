"""OpenAI tool schemas + dispatch."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from services.tools.summaries import get_company_profile, get_daily_summary

try:
    from zoneinfo import ZoneInfo

    MSK = ZoneInfo("Europe/Moscow")
except Exception:
    # Windows без tzdata / fallback
    MSK = timezone(timedelta(hours=3), name="Europe/Moscow")

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_current_datetime",
            "description": "Текущие дата и время в Europe/Moscow. Вызывай, если нужно понять «сегодня»/«вчера».",
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
            "description": "Краткий профиль NULLXES и роль Adeline Kalen.",
            "parameters": {
                "type": "object",
                "properties": {},
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


async def execute_tool(name: str, arguments_json: str) -> str:
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
    else:
        result = {"error": f"Unknown tool: {name}"}

    return json.dumps(result, ensure_ascii=False)
