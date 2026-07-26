"""Per-user state machine + experience modes + lightweight task board."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

USERS_DIR = Path(__file__).resolve().parent.parent / "data" / "users"
USERS_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_CUSTOM_ROLE: dict[str, Any] = {
    "title": "",
    "tone": "",
    "goals": [],
    "greeting": "",
    "boundaries": "",
}

# Sales FSM memory + experience modes
DEFAULT_STATE: dict[str, Any] = {
    "phase": "new",
    "intro_shown": False,
    "knows_nullxes": False,
    "miniapp_opened": False,
    "preferred_channel": "unknown",
    "display_name": "",
    "dialog_language": "",
    "user_category": "",
    "sales_stage": "start",
    "experience_mode": "showcase",
    "custom_unlocked": False,
    "custom_role": {**DEFAULT_CUSTOM_ROLE},
    "intent": "",
    "intent_confidence": 0.0,
    "dialog_memory": {
        "topics_covered": [],
        "last_intent": "",
        "last_confidence": 0.0,
        "facts": {},
    },
    "industry": "",
    "company_size": "",
    "process_goal": "",
    "why_now": "",
    "goals": [],
    "notes": "",
    "tasks": [],
    "start_count": 0,
    "message_count": 0,
    "created_at": "",
    "updated_at": "",
    "last_seen": "",
}

VALID_MODES = frozenset({"showcase", "enterprise", "custom"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _path(user_id: int) -> Path:
    return USERS_DIR / f"{user_id}.json"


def _normalize_custom_role(raw: Any) -> dict[str, Any]:
    base = {**DEFAULT_CUSTOM_ROLE}
    if not isinstance(raw, dict):
        return base
    if "title" in raw:
        base["title"] = str(raw.get("title") or "").strip()
    if "tone" in raw:
        base["tone"] = str(raw.get("tone") or "").strip()
    if "greeting" in raw:
        base["greeting"] = str(raw.get("greeting") or "").strip()
    if "boundaries" in raw:
        base["boundaries"] = str(raw.get("boundaries") or "").strip()
    if "goals" in raw:
        goals = raw.get("goals")
        if isinstance(goals, list):
            base["goals"] = [str(g).strip() for g in goals if str(g).strip()]
        elif isinstance(goals, str) and goals.strip():
            base["goals"] = [goals.strip()]
    return base


class UserStateStore:
    def __init__(self) -> None:
        self._cache: dict[int, dict[str, Any]] = {}

    def get(self, user_id: int) -> dict[str, Any]:
        if user_id in self._cache:
            return self._cache[user_id]
        path = _path(user_id)
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    merged = {**DEFAULT_STATE, **data}
                    merged["custom_role"] = _normalize_custom_role(
                        merged.get("custom_role")
                    )
                    mode = str(merged.get("experience_mode") or "showcase").lower()
                    merged["experience_mode"] = (
                        mode if mode in VALID_MODES else "showcase"
                    )
                    self._cache[user_id] = merged
                    return merged
            except Exception as exc:
                logger.warning("user state load failed %s: %s", user_id, exc)
        state = {**DEFAULT_STATE, "created_at": _now(), "custom_role": {**DEFAULT_CUSTOM_ROLE}}
        self._cache[user_id] = state
        return state

    def save(self, user_id: int, state: dict[str, Any]) -> dict[str, Any]:
        state = {**DEFAULT_STATE, **state}
        state["custom_role"] = _normalize_custom_role(state.get("custom_role"))
        mode = str(state.get("experience_mode") or "showcase").lower()
        state["experience_mode"] = mode if mode in VALID_MODES else "showcase"
        if state["experience_mode"] == "custom" and not state.get("custom_unlocked"):
            state["experience_mode"] = "showcase"
        state["updated_at"] = _now()
        state["last_seen"] = state["updated_at"]
        self._cache[user_id] = state
        try:
            _path(user_id).write_text(
                json.dumps(state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("user state save failed %s: %s", user_id, exc)
        return state

    def patch(self, user_id: int, **fields: Any) -> dict[str, Any]:
        state = dict(self.get(user_id))
        for key, value in fields.items():
            if key == "custom_role" and isinstance(value, dict):
                merged_role = _normalize_custom_role(state.get("custom_role"))
                incoming = _normalize_custom_role(value)
                for rk, rv in incoming.items():
                    if rv or rk in value:
                        merged_role[rk] = rv
                state["custom_role"] = merged_role
            elif key in DEFAULT_STATE or key in state:
                state[key] = value
        if state.get("intro_shown") and state.get("phase") in {"new", "onboarding"}:
            state["phase"] = "active"
        elif not state.get("intro_shown") and state.get("phase") == "new":
            if state.get("start_count", 0) > 0 or state.get("message_count", 0) > 0:
                state["phase"] = "onboarding"
        return self.save(user_id, state)

    def set_experience_mode(self, user_id: int, mode: str) -> dict[str, Any]:
        mode = (mode or "showcase").strip().lower()
        if mode not in VALID_MODES:
            mode = "showcase"
        if mode == "custom" and not self.get(user_id).get("custom_unlocked"):
            mode = "showcase"
        return self.patch(user_id, experience_mode=mode)

    def touch_start(self, user_id: int, display_name: str = "") -> dict[str, Any]:
        state = dict(self.get(user_id))
        state["start_count"] = int(state.get("start_count") or 0) + 1
        if display_name:
            state["display_name"] = display_name
        if not state.get("intro_shown"):
            state["phase"] = "onboarding" if state["start_count"] > 1 else "new"
        return self.save(user_id, state)

    def touch_message(self, user_id: int) -> dict[str, Any]:
        state = dict(self.get(user_id))
        state["message_count"] = int(state.get("message_count") or 0) + 1
        return self.save(user_id, state)

    def mark_intro_done(self, user_id: int) -> dict[str, Any]:
        state = self.get(user_id)
        stage = state.get("sales_stage") or "start"
        if stage in {"", "start", "greeting"}:
            mode = str(state.get("experience_mode") or "showcase")
            stage = "qualification" if mode == "enterprise" else "overview"
        return self.patch(
            user_id,
            intro_shown=True,
            knows_nullxes=True,
            phase="active",
            sales_stage=stage,
        )

    def mark_miniapp_opened(self, user_id: int) -> dict[str, Any]:
        return self.patch(user_id, miniapp_opened=True, preferred_channel="video")

    def public_view(self, user_id: int) -> dict[str, Any]:
        s = self.get(user_id)
        tasks = s.get("tasks") or []
        open_tasks = [t for t in tasks if t.get("status") != "done"]
        return {
            "phase": s.get("phase"),
            "intro_shown": s.get("intro_shown"),
            "knows_nullxes": s.get("knows_nullxes"),
            "miniapp_opened": s.get("miniapp_opened"),
            "preferred_channel": s.get("preferred_channel"),
            "display_name": s.get("display_name"),
            "dialog_language": s.get("dialog_language") or "",
            "user_category": s.get("user_category") or "",
            "sales_stage": s.get("sales_stage") or "start",
            "experience_mode": s.get("experience_mode") or "showcase",
            "custom_unlocked": bool(s.get("custom_unlocked")),
            "custom_role": s.get("custom_role") or {**DEFAULT_CUSTOM_ROLE},
            "intent": s.get("intent") or "",
            "intent_confidence": float(s.get("intent_confidence") or 0),
            "dialog_memory": s.get("dialog_memory")
            or {
                "topics_covered": [],
                "last_intent": "",
                "last_confidence": 0.0,
                "facts": {},
            },
            "industry": s.get("industry") or "",
            "company_size": s.get("company_size") or "",
            "process_goal": s.get("process_goal") or "",
            "why_now": s.get("why_now") or "",
            "goals": s.get("goals") or [],
            "notes": s.get("notes") or "",
            "open_tasks_count": len(open_tasks),
            "tasks_preview": open_tasks[:8],
            "start_count": s.get("start_count"),
            "message_count": s.get("message_count"),
        }

    def create_task(
        self,
        user_id: int,
        title: str,
        due: str = "",
        notes: str = "",
    ) -> dict[str, Any]:
        state = dict(self.get(user_id))
        tasks = list(state.get("tasks") or [])
        task = {
            "id": uuid.uuid4().hex[:10],
            "title": title.strip(),
            "status": "open",
            "due": due.strip(),
            "notes": notes.strip(),
            "created_at": _now(),
        }
        tasks.append(task)
        state["tasks"] = tasks[-50:]
        self.save(user_id, state)
        return task

    def list_tasks(self, user_id: int, include_done: bool = False) -> list[dict]:
        tasks = list(self.get(user_id).get("tasks") or [])
        if include_done:
            return tasks
        return [t for t in tasks if t.get("status") != "done"]

    def update_task(
        self,
        user_id: int,
        task_id: str,
        status: str | None = None,
        title: str | None = None,
        notes: str | None = None,
    ) -> dict[str, Any] | None:
        state = dict(self.get(user_id))
        tasks = list(state.get("tasks") or [])
        found = None
        for t in tasks:
            if t.get("id") == task_id:
                if status:
                    t["status"] = status
                if title is not None:
                    t["title"] = title
                if notes is not None:
                    t["notes"] = notes
                t["updated_at"] = _now()
                found = t
                break
        if found:
            state["tasks"] = tasks
            self.save(user_id, state)
        return found


user_states = UserStateStore()


def greeting_for(user_id: int, display_name: str) -> str:
    """Short /start — mode-aware, full greeting runs in chat / Live."""
    from prompts.adelina import greeting_for_mode, normalize_mode

    state = user_states.touch_start(user_id, display_name=display_name)
    name = display_name or "коллега"
    mode = normalize_mode(state)
    returning = bool(state.get("intro_shown") or int(state.get("start_count") or 0) > 1)
    line = greeting_for_mode(state, returning=returning).split("\n")[0]
    suffix = "/help · /voice on|off · /app"
    if returning:
        return f"{name}, {line}\n{suffix}"
    if mode == "enterprise":
        return (
            f"Здравствуйте, {name}. Аделина Кален · NULLXES · для бизнеса.\n"
            f"Откройте Mini App или напишите задачу.\n{suffix}"
        )
    return (
        f"Здравствуйте, {name}. Аделина Кален — цифровой сотрудник NULLXES.\n"
        f"Познакомиться или для бизнеса — в Mini App.\n{suffix}"
    )
