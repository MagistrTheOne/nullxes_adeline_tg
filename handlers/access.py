from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from config import settings


class AccessMiddleware(BaseMiddleware):
    """Whitelist по ALLOWED_USER_IDS. Пустой список = доступ всем."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        if not settings.allowed_user_ids:
            return await handler(event, data)

        if isinstance(event, Message) and event.from_user:
            if event.from_user.id not in settings.allowed_user_ids:
                await event.answer("Доступ закрыт. Это личный ассистент NULLXES.")
                return None

        return await handler(event, data)
