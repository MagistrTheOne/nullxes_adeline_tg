from aiogram import Dispatcher

from handlers.chat import router as chat_router
from handlers.commands import router as commands_router


def setup_routers(dp: Dispatcher) -> None:
    dp.include_router(commands_router)
    dp.include_router(chat_router)
