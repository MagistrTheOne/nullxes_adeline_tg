import asyncio
import logging

from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramNetworkError

from config import settings
from handlers import setup_routers
from handlers.access import AccessMiddleware
from routes.webapp import create_web_app
from services.anam_bridge import anam_bridge

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


async def main() -> None:
    web_app = create_web_app()
    runner = web.AppRunner(web_app)
    await runner.setup()
    site = web.TCPSite(runner, host=settings.webapp_host, port=settings.webapp_port)
    await site.start()
    logger.info(
        "Mini App HTTP на http://%s:%s | WEBAPP_PUBLIC_URL=%s",
        settings.webapp_host,
        settings.webapp_port,
        settings.webapp_public_url or "(пусто)",
    )

    try:
        await run_polling_with_retry()
    finally:
        await anam_bridge.close_all()
        await runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
