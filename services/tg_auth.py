"""Проверка Telegram WebApp initData."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from urllib.parse import parse_qsl

from config import settings

logger = logging.getLogger(__name__)


def validate_init_data(init_data: str) -> dict | None:
    """Возвращает parsed fields или None, если подпись невалидна."""
    if not init_data or not init_data.strip():
        return None

    parsed = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        return None

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(parsed.items()))
    secret_key = hmac.new(
        b"WebAppData",
        settings.bot_token.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    calculated = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(calculated, received_hash):
        logger.warning("Invalid Telegram initData hash")
        return None
    return parsed


def user_id_from_init_data(parsed: dict) -> int | None:
    raw = parsed.get("user")
    if not raw:
        return None
    try:
        user = json.loads(raw)
        return int(user.get("id"))
    except (json.JSONDecodeError, TypeError, ValueError):
        return None


def is_user_allowed(user_id: int | None) -> bool:
    if not settings.allowed_user_ids:
        return True
    if user_id is None:
        return False
    return user_id in settings.allowed_user_ids
