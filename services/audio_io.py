"""Конвертация аудио между Telegram (ogg/opus) и PCM для Anam."""

from __future__ import annotations

import io
import logging
import wave

from pydub import AudioSegment  # pyright: ignore[reportMissingImports]

logger = logging.getLogger(__name__)


def ogg_bytes_to_pcm(ogg_bytes: bytes) -> tuple[bytes, int, int]:
    """Telegram voice (.ogg) -> 16-bit PCM bytes, sample_rate, channels."""
    audio = AudioSegment.from_file(io.BytesIO(ogg_bytes), format="ogg")
    audio = audio.set_sample_width(2)
    if audio.channels > 2:
        audio = audio.set_channels(1)
    return audio.raw_data, audio.frame_rate, audio.channels


def pcm_to_wav_bytes(pcm: bytes, sample_rate: int, channels: int) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)
    return buf.getvalue()


def pcm_to_ogg_opus(pcm: bytes, sample_rate: int, channels: int) -> bytes:
    """PCM -> ogg/opus для Telegram answer_voice. Нужен ffmpeg."""
    audio = AudioSegment(
        data=pcm,
        sample_width=2,
        frame_rate=sample_rate,
        channels=channels,
    )
    out = io.BytesIO()
    try:
        audio.export(out, format="ogg", codec="libopus")
    except Exception:
        logger.warning("libopus недоступен, пробую ogg без codec=libopus")
        out = io.BytesIO()
        audio.export(out, format="ogg")
    return out.getvalue()


def pcm_to_mp3(pcm: bytes, sample_rate: int, channels: int) -> bytes:
    audio = AudioSegment(
        data=pcm,
        sample_width=2,
        frame_rate=sample_rate,
        channels=channels,
    )
    out = io.BytesIO()
    audio.export(out, format="mp3")
    return out.getvalue()
