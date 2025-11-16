# src/app/bot/main.py
import asyncio
import logging
from aiogram import Bot, Dispatcher

from src.app.bot.handlers import router
from src.app import config
from src.app.logging import setup_logging

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

    # Индексация запускается только по команде /index

    # Запуск polling с обработкой сетевых ошибок
    max_retries = 5
    retry_delay = 5.0
    
    try:
        for attempt in range(max_retries):
            try:
                await dp.start_polling(bot)
                break  # Успешный запуск
            except Exception as e:
                error_msg = str(e).lower()
                is_network_error = any(keyword in error_msg for keyword in [
                    "network", "connection", "timeout", "connector", "ssl", "telegramnetwork"
                ])
                
                if is_network_error and attempt < max_retries - 1:
                    logger.warning(
                        "Ошибка сети при запуске бота (попытка %s/%s): %s. "
                        "Повторная попытка через %s секунд...",
                        attempt + 1,
                        max_retries,
                        e,
                        retry_delay
                    )
                    await asyncio.sleep(retry_delay)
                    retry_delay *= 2  # Экспоненциальная задержка
                    continue
                else:
                    # Критическая ошибка или закончились попытки
                    logger.exception("Критическая ошибка при запуске бота: %s", e)
                    raise
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
