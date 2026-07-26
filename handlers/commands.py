from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import settings
from services.anam_bridge import anam_bridge

router = Router(name="commands")


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    name = message.from_user.full_name if message.from_user else "друг"
    text = (
        f"Привет, {name}! Я Adeline Kalen, Head of the Interworld Department NULLXES.\n"
        "Пиши текстом или голосом — отвечу. Команды: /help, /voice on|off."
    )

    if settings.webapp_public_url:
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Adeline mini app",
            web_app=WebAppInfo(url=settings.webapp_public_url.rstrip("/") + "/"),
        )
        await message.answer(text, reply_markup=builder.as_markup())
    else:
        await message.answer(
            text
            + "\n\nMini App: задай WEBAPP_PUBLIC_URL (HTTPS tunnel) и перезапусти бота."
        )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Я Adeline Kalen (NULLXES B2B).\n\n"
        "• Текст — мозг OpenAI, ответ текстом\n"
        "• Голосовое — Whisper → ответ текстом + голос Anam\n"
        "• /voice on — всегда дублировать ответ голосом Anam\n"
        "• /voice off — голос только на voice-сообщения\n"
        "• Mini App — Home + Live аватар (нужен HTTPS WEBAPP_PUBLIC_URL)\n"
        "• Сводки — tool get_daily_summary (без файла = честный fallback)\n\n"
        "Важно: в Anam Lab у persona LLM = CUSTOMER_CLIENT_V1 "
        "(brain на стороне NULLXES)."
    )


@router.message(Command("voice"))
async def cmd_voice(message: Message, command: CommandObject) -> None:
    if not message.from_user:
        return
    arg = (command.args or "").strip().lower()
    if arg not in {"on", "off"}:
        state = "on" if anam_bridge.is_voice_force(message.from_user.id) else "off"
        await message.answer(f"Сейчас /voice = {state}. Пример: /voice on")
        return

    enabled = arg == "on"
    anam_bridge.set_voice_force(message.from_user.id, enabled)
    await message.answer(
        "Голосовые ответы всегда включены." if enabled else "Голос только на voice-сообщения."
    )
