"""HTTP API + static dist для Telegram Mini App."""

from __future__ import annotations

import logging
from pathlib import Path

import aiohttp
from aiohttp import web

from config import settings
from services.llm import brain
from services.tg_auth import is_user_allowed, user_id_from_init_data, validate_init_data

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parent.parent
DIST_DIR = ROOT / "miniapp" / "dist"
ANAM_SESSION_URL = "https://api.anam.ai/v1/auth/session-token"


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


async def create_session_token(request: web.Request) -> web.Response:
    user_id, err = _auth_user(request)
    if err:
        return err

    # Stateful Lab persona (CUSTOMER_CLIENT / LLM disabled). Greeting via our brain + talk().
    payload = {"personaConfig": {"personaId": settings.anam_persona_id}}
    headers = {
        "Authorization": f"Bearer {settings.anam_api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                ANAM_SESSION_URL,
                json=payload,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as resp:
                body = await resp.json(content_type=None)
                if resp.status >= 400:
                    logger.error("Anam session-token error %s: %s", resp.status, body)
                    return web.json_response(
                        {"error": "anam_session_failed", "details": body},
                        status=502,
                    )
                return web.json_response(
                    {
                        "sessionToken": body.get("sessionToken")
                        or body.get("session_token"),
                        "personaId": settings.anam_persona_id,
                        "avatarId": settings.anam_avatar_id,
                        "userId": user_id,
                        "name": "Adeline Kalen",
                        "role": "Head of the Interworld Department NULLXES",
                    }
                )
    except Exception as exc:
        logger.exception("session-token request failed")
        return web.json_response({"error": str(exc)}, status=500)


async def history_handler(request: web.Request) -> web.Response:
    user_id, err = _auth_user(request)
    if err:
        return err
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
            "role": "Head of the Interworld Department NULLXES",
            "title": "Enterprise Executive",
            "status": "Online · ready",
            "personaId": settings.anam_persona_id,
            "avatarId": settings.anam_avatar_id,
            "imageUrl": image_url,
            "blurb": (
                "Ваш цифровой ассистент NULLXES. Пишите в чат, "
                "звоните голосом или выходите в живой видео-разговор."
            ),
            "badges": {"avatar": "ready", "voice": "ready", "brain": "client"},
            "preset": "Enterprise Closer",
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
