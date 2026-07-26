"""Anam TTS/voice bridge.

Persona Adeline в Lab = CUSTOMER_CLIENT_V1 (LLM disabled):
мозг — OpenAI, Anam — озвучка через session.talk() + audio_frames.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field

from anam import (  # pyright: ignore[reportMissingImports]
    AnamClient,
    AnamEvent,
    Message,
    MessageRole,
    SessionOptions,
)
from anam.client import Session  # pyright: ignore[reportMissingImports]

from config import settings
from services.pronounce import for_speech

logger = logging.getLogger(__name__)


@dataclass
class SpokenReply:
    text: str
    audio_pcm: bytes = b""
    sample_rate: int = 48000
    channels: int = 2


@dataclass
class _SpeakState:
    done: asyncio.Event = field(default_factory=asyncio.Event)
    session_ready: asyncio.Event = field(default_factory=asyncio.Event)
    audio_buffer: bytearray = field(default_factory=bytearray)
    sample_rate: int = 48000
    channels: int = 2
    collecting: bool = False


class AnamBridge:
    def __init__(self) -> None:
        self._voice_force: dict[int, bool] = {}
        self._locks: dict[int, asyncio.Lock] = {}

    def set_voice_force(self, user_id: int, enabled: bool) -> None:
        self._voice_force[user_id] = enabled

    def is_voice_force(self, user_id: int) -> bool:
        return self._voice_force.get(user_id, False)

    def _lock_for(self, user_id: int) -> asyncio.Lock:
        if user_id not in self._locks:
            self._locks[user_id] = asyncio.Lock()
        return self._locks[user_id]

    async def close_all(self) -> None:
        return

    async def speak(self, user_id: int, text: str) -> SpokenReply:
        """Озвучить готовый текст голосом persona через Anam talk()."""
        if not text.strip():
            return SpokenReply(text=text)

        async with self._lock_for(user_id):
            state = _SpeakState()
            client = AnamClient(
                api_key=settings.anam_api_key,
                persona_id=settings.anam_persona_id,
            )

            @client.on(AnamEvent.SESSION_READY)
            async def _on_ready() -> None:
                state.session_ready.set()

            @client.on(AnamEvent.MESSAGE_RECEIVED)
            async def _on_message(message: Message) -> None:
                if message.role == MessageRole.ASSISTANT:
                    state.done.set()

            async with client.connect(
                session_options=SessionOptions(video_quality="auto")
            ) as session:
                tasks = [
                    asyncio.create_task(self._drain_video(session)),
                    asyncio.create_task(self._collect_audio(session, state)),
                ]
                try:
                    try:
                        await asyncio.wait_for(state.session_ready.wait(), timeout=20.0)
                    except asyncio.TimeoutError:
                        logger.warning("SESSION_READY timeout user=%s", user_id)

                    await asyncio.sleep(0.4)
                    state.collecting = True
                    await session.talk(for_speech(text))

                    try:
                        await asyncio.wait_for(
                            state.done.wait(),
                            timeout=settings.anam_reply_timeout,
                        )
                    except asyncio.TimeoutError:
                        logger.warning("Anam talk timeout user=%s", user_id)

                    await asyncio.sleep(1.2)
                    state.collecting = False
                    await asyncio.sleep(0.3)

                    return SpokenReply(
                        text=text,
                        audio_pcm=bytes(state.audio_buffer),
                        sample_rate=state.sample_rate,
                        channels=state.channels,
                    )
                finally:
                    state.collecting = False
                    for task in tasks:
                        task.cancel()
                    await asyncio.gather(*tasks, return_exceptions=True)

    async def _drain_video(self, session: Session) -> None:
        try:
            async for _ in session.video_frames():
                pass
        except asyncio.CancelledError:
            return
        except Exception as exc:
            logger.debug("video drain ended: %s", exc)

    async def _collect_audio(self, session: Session, state: _SpeakState) -> None:
        try:
            async for frame in session.audio_frames():
                if not state.collecting:
                    continue
                samples = frame.to_ndarray()
                state.sample_rate = frame.sample_rate
                state.channels = frame.layout.nb_channels
                state.audio_buffer.extend(samples.astype("int16").tobytes())
        except asyncio.CancelledError:
            return
        except Exception as exc:
            logger.debug("audio collect ended: %s", exc)


anam_bridge = AnamBridge()
