"""HTTP API + static dist для Telegram Mini App."""

from __future__ import annotations

import logging
from pathlib import Path

import aiohttp
from aiohttp import web

from config import settings
from prompts.adelina import FIRST_GREETING, RETURNING_GREETING
from services.llm import brain
from services.tg_auth import is_user_allowed, user_id_from_init_data, validate_init_data
from services.user_state import user_states

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "miniapp" / "dist"
ANAM_SESSION_URL = "https://api.anam.ai/v1/auth/session-token"
ANAM_VOICE_URL = "https://api.anam.ai/v1/voices/{voice_id}"


def _auth_user(request: web.Request) -> tuple[int | None, web.Response | None]:
    """Returns (user_id, error_response)."""
    init_data = request.headers.get("X-Telegram-Init-Data", "").strip()
    if settings.webapp_skip_auth and not init_data:
        return 0, None

    parsed = validate_init_data(init_data)
    if parsed is None:
        return None, web.json_response({"error": "invalid_init_data"}, status=401)

    user_id = user_id_from_init_data(parsed)
    if not is_user_allowed(user_id):
        return None, web.json_response({"error": "forbidden"}, status=403)
    return user_id, None


async def _voice_usable(
    session: aiohttp.ClientSession,
    headers: dict[str, str],
    voice_id: str,
) -> bool:
    """ElevenLabs imports often return 200 but stay silent until sampleUrl exists."""
    if not voice_id:
        return False
    try:
        async with session.get(
            ANAM_VOICE_URL.format(voice_id=voice_id),
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=12),
        ) as resp:
            if resp.status >= 400:
                return False
            body = await resp.json(content_type=None)
            provider = str(body.get("provider") or "").upper()
            sample = body.get("sampleUrl") or body.get("previewSampleUrl")
            if provider == "ELEVENLABS" and not sample:
                logger.warning(
                    "ElevenLabs voice %s not ready (no sampleUrl) — will use Anam fallback",
                    voice_id,
                )
                return False
            return True
    except Exception as exc:
        logger.warning("voice probe failed %s: %s", voice_id, exc)
        return False


async def _resolve_voice_ids(
    session: aiohttp.ClientSession,
    headers: dict[str, str],
) -> list[str]:
    """Primary ElevenLabs (if ready), then stock Anam female fallback."""
    primary = settings.anam_voice_id.strip()
    fallback = settings.anam_voice_fallback_id.strip()
    ordered: list[str] = []
    if primary and await _voice_usable(session, headers, primary):
        ordered.append(primary)
    elif primary:
        logger.warning("Skipping unusable primary voice %s", primary)
    if fallback and fallback not in ordered:
        ordered.append(fallback)
    if primary and primary not in ordered:
        # Last resort: still try primary if probe lied / transient.
        ordered.append(primary)
    return ordered


async def create_session_token(request: web.Request) -> web.Response:
    user_id, err = _auth_user(request)
    if err:
        return err

    if user_id:
        user_states.mark_miniapp_opened(int(user_id))
        user_states.patch(int(user_id), preferred_channel="video")

    # CUSTOMER_CLIENT persona: Anam = face/voice/STT; NULLXES OpenAI = brain.
    intro_shown = False
    if user_id:
        intro_shown = bool(user_states.get(int(user_id)).get("intro_shown"))

    headers = {
        "Authorization": f"Bearer {settings.anam_api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with aiohttp.ClientSession() as session:
            voice_ids = await _resolve_voice_ids(session, headers)
            if not voice_ids:
                voice_ids = [settings.anam_voice_fallback_id]

            last_error: object = None
            for voice_id in voice_ids:
                persona_config: dict = {
                    "personaId": settings.anam_persona_id,
                    "maxSessionLengthSeconds": settings.anam_max_session_seconds,
                    "skipGreeting": True,
                    "languageCode": "ru",
                    "voiceId": voice_id,
                    "directorNotes": {
                        "expressivity": 0.5,
                        "customStylePrompt": "спокойная",
                    },
                }
                if settings.anam_avatar_id:
                    persona_config["avatarId"] = settings.anam_avatar_id
                payload = {"personaConfig": persona_config}
                async with session.post(
                    ANAM_SESSION_URL,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as resp:
                    body = await resp.json(content_type=None)
                    if resp.status >= 400:
                        last_error = body
                        logger.error(
                            "Anam session-token error voice=%s %s: %s",
                            voice_id,
                            resp.status,
                            body,
                        )
                        continue

                    logger.info("Live session voice=%s", voice_id)
                    greeting = RETURNING_GREETING if intro_shown else FIRST_GREETING
                    if user_id and not intro_shown:
                        user_states.mark_intro_done(int(user_id))
                    return web.json_response(
                        {
                            "sessionToken": body.get("sessionToken")
                            or body.get("session_token"),
                            "personaId": settings.anam_persona_id,
                            "avatarId": settings.anam_avatar_id,
                            "voiceId": voice_id,
                            "userId": user_id,
                            "name": "Adeline Kalen",
                            "role": "Аделина Кален · NULLXES",
                            "greeting": greeting,
                            "speakGreeting": True,
                            "languageCode": "ru",
                        }
                    )

            return web.json_response(
                {"error": "anam_session_failed", "details": last_error},
                status=502,
            )
    except Exception as exc:
        logger.exception("session-token request failed")
        return web.json_response({"error": str(exc)}, status=500)


async def history_handler(request: web.Request) -> web.Response:
    user_id, err = _auth_user(request)
    if err:
        return err
    if user_id:
        user_states.mark_miniapp_opened(int(user_id))
    return web.json_response(
        {"messages": brain.public_history(int(user_id or 0))}
    )


async def chat_handler(request: web.Request) -> web.Response:
    user_id, err = _auth_user(request)
    if err:
        return err

    try:
        body = await request.json()
    except Exception:
        return web.json_response({"error": "invalid_json"}, status=400)

    text = str(body.get("text") or "").strip()
    if not text:
        return web.json_response({"error": "text_required"}, status=400)

    try:
        uid = int(user_id or 0)
        reply = await brain.chat(uid, text)
        return web.json_response(
            {"reply": reply, "history": brain.public_history(uid)}
        )
    except Exception as exc:
        logger.exception("chat failed")
        return web.json_response({"error": str(exc)}, status=500)


async def persona_card(_: web.Request) -> web.Response:
    image_url = ""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.anam.ai/v1/personas/{settings.anam_persona_id}",
                headers={"Authorization": f"Bearer {settings.anam_api_key}"},
                timeout=aiohttp.ClientTimeout(total=15),
            ) as resp:
                if resp.status < 400:
                    data = await resp.json()
                    image_url = (data.get("avatar") or {}).get("imageUrl") or ""
    except Exception as exc:
        logger.warning("persona image fetch failed: %s", exc)

    return web.json_response(
        {
            "name": "Adeline Kalen",
            "role": "Adeline Kalen из NULLXES",
            "title": "Digital executive",
            "status": "Online · ready",
            "personaId": settings.anam_persona_id,
            "avatarId": settings.anam_avatar_id,
            "imageUrl": image_url,
            "blurb": (
                "Цифровая сотрудница NULLXES. Мы создаём цифровых сотрудников "
                "для компаний и персональных цифровых друзей. "
                "Пишите, звоните голосом или наберите по видео."
            ),
            "badges": {"avatar": "ready", "voice": "ready", "brain": "client"},
            "preset": "NULLXES",
        }
    )


async def spa_index(_: web.Request) -> web.FileResponse:
    index = DIST_DIR / "index.html"
    if not index.exists():
        raise web.HTTPNotFound(
            text="miniapp/dist not found. Run: cd miniapp && npm install && npm run build"
        )
    return web.FileResponse(index)


async def spa_fallback(request: web.Request) -> web.StreamResponse:
    # API already registered; this catches client routes
    if request.path.startswith("/api/"):
        raise web.HTTPNotFound()
    return await spa_index(request)


def create_web_app() -> web.Application:
    app = web.Application()
    app.router.add_get("/api/persona", persona_card)
    app.router.add_post("/api/session-token", create_session_token)
    app.router.add_get("/api/history", history_handler)
    app.router.add_post("/api/chat", chat_handler)
    app.router.add_get("/webapp/session-token", create_session_token)
    app.router.add_post("/webapp/session-token", create_session_token)

    if DIST_DIR.exists():
        app.router.add_static("/assets/", DIST_DIR / "assets", show_index=False)
        # vite may emit other hashed files at root
        app.router.add_get("/", spa_index)
        app.router.add_get("/{tail:.*}", spa_fallback)
    else:
        async def missing(_: web.Request) -> web.Response:
            return web.Response(
                text="Build Mini App first: cd miniapp && npm install && npm run build",
                status=503,
            )

        app.router.add_get("/", missing)

    return app
