import logging

from aiogram import Bot, F, Router
from aiogram.enums import ChatAction
from aiogram.types import BufferedInputFile, Message

from services.anam_bridge import anam_bridge
from services.audio_io import pcm_to_mp3, pcm_to_ogg_opus
from services.llm import brain

logger = logging.getLogger(__name__)
router = Router(name="chat")


async def _send_voice_reply(
    message: Message,
    pcm: bytes,
    sample_rate: int,
    channels: int,
) -> None:
    if not pcm:
        return
    try:
        ogg = pcm_to_ogg_opus(pcm, sample_rate, channels)
        await message.answer_voice(BufferedInputFile(ogg, filename="adelina.ogg"))
    except Exception as exc:
        logger.warning("answer_voice failed (%s), пробую mp3", exc)
        mp3 = pcm_to_mp3(pcm, sample_rate, channels)
        await message.answer_audio(BufferedInputFile(mp3, filename="adelina.mp3"))


@router.message(F.voice)
async def on_voice(message: Message, bot: Bot) -> None:
    if not message.from_user or not message.voice:
        return

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        buf = await bot.download(message.voice)
        if buf is None:
            raise RuntimeError("Не удалось скачать voice")
        ogg_bytes = buf.read()

        user_text = await brain.transcribe(ogg_bytes)
        if not user_text:
            await message.answer("Не разобрала речь. Попробуй ещё раз.")
            return

        reply_text = await brain.chat(message.from_user.id, user_text)
        await message.answer(reply_text)

        await bot.send_chat_action(message.chat.id, ChatAction.RECORD_VOICE)
        spoken = await anam_bridge.speak(message.from_user.id, reply_text)
        await _send_voice_reply(
            message,
            spoken.audio_pcm,
            spoken.sample_rate,
            spoken.channels,
        )
    except Exception as exc:
        logger.exception("voice chat failed")
        await message.answer(f"Ошибка: {exc}")


@router.message(F.text & ~F.text.startswith("/"))
async def on_text(message: Message, bot: Bot) -> None:
    if not message.from_user or not message.text:
        return

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    try:
        reply_text = await brain.chat(message.from_user.id, message.text)
        await message.answer(reply_text)

        if anam_bridge.is_voice_force(message.from_user.id):
            await bot.send_chat_action(message.chat.id, ChatAction.RECORD_VOICE)
            spoken = await anam_bridge.speak(message.from_user.id, reply_text)
            await _send_voice_reply(
                message,
                spoken.audio_pcm,
                spoken.sample_rate,
                spoken.channels,
            )
    except Exception as exc:
        logger.exception("text chat failed")
        await message.answer(f"Ошибка: {exc}")
