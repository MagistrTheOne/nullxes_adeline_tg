from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import settings
from services.anam_bridge import anam_bridge
from services.user_state import greeting_for, user_states

router = Router(name="commands")


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    name = message.from_user.full_name if message.from_user else "друг"
    user_id = message.from_user.id if message.from_user else 0
    text, _first = greeting_for(user_id, name)

    if settings.webapp_public_url:
        builder = InlineKeyboardBuilder()
        builder.button(
            text="Открыть Adeline",
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
        "Я Adeline Kalen из NULLXES — цифровая сотрудница "
        "(Head of the Interworld Department).\n\n"
        "NULLXES создаёт цифровых сотрудников для компаний и персональных цифровых друзей.\n\n"
        "• Текст / голос / видео в Mini App\n"
        "• Могу вести задачи и план через диалог\n"
        "• /voice on|off — дублировать ответы голосом\n"
        "• /memory — что я о вас помню\n"
        "• Сводки — get_daily_summary (без файла = честный ответ)"
    )


@router.message(Command("memory"))
async def cmd_memory(message: Message) -> None:
    if not message.from_user:
        return
    view = user_states.public_view(message.from_user.id)
    goals = view.get("goals") or []
    tasks = view.get("tasks_preview") or []
    goals_s = ", ".join(goals) if goals else "—"
    tasks_s = (
        "\n".join(f"• [{t.get('status')}] {t.get('title')}" for t in tasks)
        if tasks
        else "—"
    )
    await message.answer(
        "Память:\n"
        f"Фаза: {view.get('phase')}\n"
        f"Интро было: {'да' if view.get('intro_shown') else 'нет'}\n"
        f"Mini App: {'открывали' if view.get('miniapp_opened') else 'ещё нет'}\n"
        f"Цели: {goals_s}\n"
        f"Задачи:\n{tasks_s}"
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
    if enabled:
        user_states.patch(message.from_user.id, preferred_channel="voice")
    await message.answer(
        "Голосовые ответы всегда включены." if enabled else "Голос только на voice-сообщения."
    )
