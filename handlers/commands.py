from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.types import MenuButtonWebApp, Message, WebAppInfo
from aiogram.utils.keyboard import InlineKeyboardBuilder

from config import get_webapp_public_url, settings
from services.anam_bridge import anam_bridge
from services.user_state import greeting_for, user_states

router = Router(name="commands")


async def _send_webapp_button(message: Message, text: str) -> None:
    public_url = get_webapp_public_url()
    if not public_url:
        await message.answer(
            text
            + "\n\nMini App: туннель ещё поднимается — подожди 5–10 секунд и снова /start."
        )
        return

    app_url = public_url.rstrip("/") + "/"
    builder = InlineKeyboardBuilder()
    builder.button(text="Открыть Adeline", web_app=WebAppInfo(url=app_url))
    await message.answer(text, reply_markup=builder.as_markup())

    # Per-chat menu button always points at the live tunnel URL.
    if message.chat:
        try:
            await message.bot.set_chat_menu_button(
                chat_id=message.chat.id,
                menu_button=MenuButtonWebApp(
                    text="Adeline",
                    web_app=WebAppInfo(url=app_url),
                ),
            )
        except Exception:
            pass


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    name = message.from_user.full_name if message.from_user else "друг"
    user_id = message.from_user.id if message.from_user else 0
    text = greeting_for(user_id, name)
    await _send_webapp_button(message, text)


@router.message(Command("app"))
async def cmd_app(message: Message) -> None:
    await _send_webapp_button(
        message,
        "Актуальная кнопка Mini App (если старая даёт 503 — жми эту):",
    )



@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "Я Adeline Kalen из NULLXES — цифровая сотрудница "
        "(Head of the Interworld Department).\n\n"
        "NULLXES создаёт цифровых сотрудников для компаний и персональных цифровых друзей.\n\n"
        "• Текст / голос / видео в Mini App\n"
        "• /start или /app — актуальная кнопка Mini App\n"
        "• /voice on|off — дублировать ответы голосом\n"
        "• /memory — что я о вас помню\n"
        "Если Mini App пишет 503 — снова /start (туннель сменил URL)."
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
