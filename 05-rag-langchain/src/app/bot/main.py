# src/app/bot/main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher

from src.app.bot.handlers import router
from src.app import config
from src.app.logging import setup_logging
from src.app.indexing import run_full_indexing

logger = logging.getLogger(__name__)

async def main() -> None:
    # Настройка логирования
    setup_logging()
    logger.info("Запуск Telegram-бота...")

    # Инициализация бота и диспетчера
    bot = Bot(token=config.TELEGRAM_BOT_TOKEN)
    dp = Dispatcher()

    # Регистрация роутера с обработчиками
    dp.include_router(router)

    # Переиндексация данных при старте (в фоне, чтобы не блокировать запуск бота)
    asyncio.create_task(run_full_indexing())

    # Запуск polling
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
        logger.info("Telegram-бот остановлен.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем.")
    except Exception as e:
        logger.exception(f"Произошла непредвиденная ошибка: {e}")
