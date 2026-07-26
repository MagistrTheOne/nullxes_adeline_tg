"""Мозг Аделины: OpenAI Chat + tools (+ Whisper STT).

Persona в Anam Lab = CUSTOMER_CLIENT_V1 — LLM на стороне NULLXES.
История общая для Telegram и Mini App, хранится в data/chats/.
"""

from __future__ import annotations

import io
import json
import logging
from collections import defaultdict
from pathlib import Path

from openai import AsyncOpenAI  # pyright: ignore[reportMissingImports]

from config import settings
from prompts.adelina import SYSTEM_PROMPT
from services.tools.registry import TOOL_DEFINITIONS, execute_tool

logger = logging.getLogger(__name__)

MAX_TOOL_ROUNDS = 6
MAX_HISTORY = 40
CHATS_DIR = Path(__file__).resolve().parent.parent / "data" / "chats"


class AdelinaBrain:
    def __init__(self) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)
        self._history: dict[int, list[dict]] = defaultdict(list)
        self._loaded: set[int] = set()
        CHATS_DIR.mkdir(parents=True, exist_ok=True)

    def _path(self, user_id: int) -> Path:
        return CHATS_DIR / f"{user_id}.json"

    def _ensure_loaded(self, user_id: int) -> None:
        if user_id in self._loaded:
            return
        self._loaded.add(user_id)
        path = self._path(user_id)
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(data, list):
                self._history[user_id] = data
        except Exception as exc:
            logger.warning("chat history load failed user=%s: %s", user_id, exc)

    def _save(self, user_id: int) -> None:
        path = self._path(user_id)
        try:
            path.write_text(
                json.dumps(self._history[user_id], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("chat history save failed user=%s: %s", user_id, exc)

    def reset(self, user_id: int) -> None:
        self._history.pop(user_id, None)
        self._loaded.discard(user_id)
        path = self._path(user_id)
        if path.exists():
            path.unlink(missing_ok=True)

    def public_history(self, user_id: int) -> list[dict]:
        """User/assistant text turns for Mini App UI (no tools/system)."""
        self._ensure_loaded(user_id)
        out: list[dict] = []
        for msg in self._history[user_id]:
            role = msg.get("role")
            content = (msg.get("content") or "").strip()
            if role in ("user", "assistant") and content and not msg.get("tool_calls"):
                out.append({"role": role, "content": content})
        return out

    async def chat(self, user_id: int, user_text: str) -> str:
        self._ensure_loaded(user_id)
        history = self._history[user_id]
        history.append({"role": "user", "content": user_text})
        if len(history) > MAX_HISTORY:
            del history[:-MAX_HISTORY]

        messages: list[dict] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            *history,
        ]

        reply = ""
        for _ in range(MAX_TOOL_ROUNDS):
            response = await self._client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                tools=TOOL_DEFINITIONS,
                tool_choice="auto",
                temperature=0.5,
            )
            choice = response.choices[0].message
            tool_calls = choice.tool_calls or []

            if tool_calls:
                assistant_msg: dict = {
                    "role": "assistant",
                    "content": choice.content or "",
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments or "{}",
                            },
                        }
                        for tc in tool_calls
                    ],
                }
                messages.append(assistant_msg)
                history.append(assistant_msg)

                for tc in tool_calls:
                    result = await execute_tool(
                        tc.function.name,
                        tc.function.arguments or "{}",
                    )
                    logger.info("tool %s -> %s", tc.function.name, result[:200])
                    tool_msg = {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                    messages.append(tool_msg)
                    history.append(tool_msg)
                continue

            reply = (choice.content or "").strip()
            break

        if not reply:
            reply = "Не смогла сформировать ответ. Попробуй переформулировать."

        history.append({"role": "assistant", "content": reply})
        self._save(user_id)
        return reply

    async def transcribe(self, ogg_bytes: bytes) -> str:
        bio = io.BytesIO(ogg_bytes)
        bio.name = "voice.ogg"
        result = await self._client.audio.transcriptions.create(
            model="whisper-1",
            file=bio,
        )
        text = (result.text or "").strip()
        logger.info("Whisper: %s", text[:120])
        return text


brain = AdelinaBrain()
