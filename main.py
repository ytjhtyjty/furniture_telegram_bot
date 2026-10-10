import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import DeleteWebhook
from aiogram.types import BotCommand, BotCommandScopeChat

from settings.config import ConfigBot
from handlers.admin import router as admin_router
from handlers.backend import router as backend_router

from database.engine import async_engine, Base
from database import models

from utils.filters import IsAdmin


async def init_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
        except Exception:
            # Админ мог ещё ни разу не писать боту — тогда чата нет, это нормально
            logging.warning("Не удалось задать команды для админа %s", admin_id)

async def main():
    # Настраиваем подробный вывод логов в консоль
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
    )

    if not ConfigBot.TOKEN:
        logging.critical("BOT_TOKEN не задан. Создайте файл .env по образцу .env.example")
        return 
    if not ConfigBot.ADMIN_IDS:
        logging.critical("ADMIN_IDS пуст: админ-панель сейчас некому не доступна")

    await init_db()

    # Создаем бота с поддержкой HTML-разметки
    bot = Bot(token=ConfigBot.TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Админский роутер
    admin_router.message.filter(IsAdmin())
    admin_router.callback_query.filter(IsAdmin())

    # Подключаем роутеры
    dp.include_router(admin_router)
    dp.include_router(backend_router)

    try:
        # Удаляем вебхуки и старые сообщения, пришедшие во время отключения
        await bot(DeleteWebhook(drop_pending_updates=True))
        await set_commands(bot)
        logging.info("🚀 Бот мебельной компании успешно запущен!")
        await dp.start_polling(bot, skip_updates=True)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except TelegramBadRequest as e:
        logging.error(f"Telegram API error: {e}")
    except KeyboardInterrupt:
        logging.info("Бот выключен вручную.")
    except Exception as e:
        logging.critical(f"Критический сбой: {e}", exc_info=True)