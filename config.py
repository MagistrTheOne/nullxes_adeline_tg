import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    bot_token: str
    openai_api_key: str
    openai_model: str
    anam_api_key: str
    anam_persona_id: str
    anam_avatar_id: str
    anam_voice_id: str
    allowed_user_ids: frozenset[int]
    anam_reply_timeout: float = 45.0
    webapp_host: str = "0.0.0.0"
    webapp_port: int = 8080
    webapp_public_url: str = ""
    webapp_skip_auth: bool = False


def _parse_allowed_ids(raw: str | None) -> frozenset[int]:
    if not raw or not raw.strip():
        return frozenset()
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part:
            ids.add(int(part))
    return frozenset(ids)


def load_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    anam_api_key = os.getenv("ANAM_API_KEY", "").strip()
    anam_persona_id = os.getenv("ANAM_PERSONA_ID", "").strip()
    anam_avatar_id = os.getenv("ANAM_AVATAR_ID", "").strip()
    anam_voice_id = os.getenv("ANAM_VOICE_ID", "").strip()

    missing = [
        name
        for name, value in (
            ("BOT_TOKEN", bot_token),
            ("OPENAI_API_KEY", openai_api_key),
            ("ANAM_API_KEY", anam_api_key),
            ("ANAM_PERSONA_ID", anam_persona_id),
        )
        if not value
    ]
    if missing:
        raise ValueError(f"Не найдены переменные в .env: {', '.join(missing)}")

    allowed = _parse_allowed_ids(os.getenv("ALLOWED_USER_IDS"))
    if not allowed:
        logger.warning(
            "ALLOWED_USER_IDS пуст — whitelist отключён. Добавь свой Telegram id в .env."
        )

    return Settings(
        bot_token=bot_token,
        openai_api_key=openai_api_key,
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
        anam_api_key=anam_api_key,
        anam_persona_id=anam_persona_id,
        anam_avatar_id=anam_avatar_id,
        anam_voice_id=anam_voice_id,
        allowed_user_ids=allowed,
        webapp_public_url=os.getenv("WEBAPP_PUBLIC_URL", "").strip(),
        webapp_port=int(os.getenv("WEBAPP_PORT", "8080")),
        webapp_skip_auth=os.getenv("WEBAPP_SKIP_AUTH", "").strip().lower()
        in {"1", "true", "yes"},
    )


settings = load_settings()
