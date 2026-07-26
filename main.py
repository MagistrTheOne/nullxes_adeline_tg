import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError
from aiogram.types import MenuButtonWebApp, WebAppInfo

from config import get_webapp_public_url, settings
from handlers import setup_routers
from handlers.access import AccessMiddleware
from routes.webapp import create_web_app
from services.anam_bridge import anam_bridge
from services.tunnel import (
    start_localhost_run_tunnel,
    stop_tunnel,
    tunnel_enabled,
    wait_for_public_url,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)

bot = Bot(
    token=settings.bot_token,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()
dp.message.middleware(AccessMiddleware())
setup_routers(dp)


async def run_polling_with_retry() -> None:
    """Telegram API может быть недоступен без VPN — HTTP Mini App при этом живёт."""
    delay = 5
    while True:
        try:
            await bot.delete_webhook(drop_pending_updates=True)
            logger.info("Telegram polling start…")
            await dp.start_polling(bot)
            return
        except TelegramNetworkError as exc:
            logger.warning(
                "Telegram недоступен (%s). Retry через %ss. Mini App HTTP продолжает работать.",
                exc,
                delay,
            )
            await asyncio.sleep(delay)
            delay = min(delay * 2, 60)
        except asyncio.CancelledError:
            raise


async def sync_webapp_menu_button(url: str, chat_id: int | None = None) -> None:
    """Keep Telegram menu / WebApp button on the live tunnel URL."""
    url = (url or "").rstrip("/") + "/"
    await bot.set_chat_menu_button(
        chat_id=chat_id,
        menu_button=MenuButtonWebApp(
            text="Adeline",
            web_app=WebAppInfo(url=url),
        ),
    )
    scope = f"chat={chat_id}" if chat_id else "default"
    logger.info("Telegram menu button (%s) -> %s", scope, url)


async def main() -> None:
    web_app = create_web_app()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, host=settings.webapp_host, port=settings.webapp_port)
    await site.start()
    logger.info(
        "Mini App HTTP на http://%s:%s",
        settings.webapp_host,
        settings.webapp_port,
    )

    tunnel_task: asyncio.Task | None = None
    if tunnel_enabled():
        tunnel_task = asyncio.create_task(
            start_localhost_run_tunnel(
                settings.webapp_port,
                on_url=sync_webapp_menu_button,
            ),
            name="localhost-run-tunnel",
        )
        url = await wait_for_public_url(timeout=45)
        if url:
            logger.info("Туннель готов: %s — жми /start в Telegram", url)
            try:
                await sync_webapp_menu_button(url)
            except Exception as exc:
                logger.warning("Не удалось обновить menu button: %s", exc)
        else:
            logger.warning(
                "Туннель не выдал URL за 45с. Mini App локально на :%s",
                settings.webapp_port,
            )
    else:
        current = get_webapp_public_url()
        if current:
            try:
                await sync_webapp_menu_button(current)
            except Exception as exc:
                logger.warning("Не удалось обновить menu button: %s", exc)

    try:
        await run_polling_with_retry()
    finally:
        if tunnel_task:
            tunnel_task.cancel()
            try:
                await tunnel_task
            except asyncio.CancelledError:
                pass
        await stop_tunnel()
        await anam_bridge.close_all()
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
