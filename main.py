import asyncio
import logging
import os
import sqlite3

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotCommand, BotCommandScopeChat, ErrorEvent
from alembic import command
from alembic.config import Config

from settings.config import ConfigBot
from handlers.admin import router as admin_router
from handlers.backend import router as backend_router
from utils.logger import setup_logging, shutdown_logging
from utils.middlewares import LoggingMiddleware

from database.engine import async_engine, DB_PATH

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INITIAL_REVISION = "0001_initial"


def run_migrations() -> None:
    cfg = Config(os.path.join(BASE_DIR, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(BASE_DIR, "alembic"))
    cfg.attributes["configure_logger"] = False

    if os.path.exists(DB_PATH):
        with sqlite3.connect(DB_PATH) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        if "categories" in tables and "alembic_version" not in tables:
            logging.info("Найдена база без Alembic — помечаю ревизией %s", INITIAL_REVISION)
            command.stamp(cfg, INITIAL_REVISION)

    command.upgrade(cfg, "head")


async def init_db():
    await asyncio.to_thread(run_migrations)


async def set_commands(bot: Bot):
    common = [
        BotCommand(command="start", description="Главное меню"),
    ]
    await bot.set_my_commands(common)

    admin_commands = common + [
        BotCommand(command="admin_panel", description="Панель администратора")
    ]
    for admin_id in ConfigBot.ADMIN_IDS:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
        except TelegramAPIError:
            logging.warning("Не удалось задать команды для админа %s", admin_id)


async def on_error(event: ErrorEvent):
    logging.exception("Ошибка при обработке апдейта", exc_info=event.exception)
    callback = event.update.callback_query
    message = event.update.message
    try:
        if callback is not None:
            await callback.answer("⚠️ Что-то пошло не так. Попробуйте ещё раз или нажмите /start.", show_alert=True)
        elif message is not None:
            await message.answer("⚠️ Что-то пошло не так. Попробуйте ещё раз или нажмите /start.")
    except TelegramAPIError:
        pass
    return True


async def main():
    if not ConfigBot.TOKEN:
        logging.critical("BOT_TOKEN не задан. Создайте файл .env по образцу .env.example")
        return
    if not ConfigBot.ADMIN_IDS:
        logging.critical("ADMIN_IDS пуст: админ-панель сейчас никому не доступна")

    await init_db()

    bot = Bot(token=ConfigBot.TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.errors.register(on_error)
    dp.update.outer_middleware(LoggingMiddleware())

    dp.include_router(admin_router)
    dp.include_router(backend_router)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await set_commands(bot)
        logging.info("🚀 Бот мебельной компании успешно запущен!")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        await async_engine.dispose()


if __name__ == '__main__':
    setup_logging()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Бот выключен вручную.")
    except Exception as e:
        logging.critical(f"Критический сбой: {e}", exc_info=True)
    finally:
        shutdown_logging()
