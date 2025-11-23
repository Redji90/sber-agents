# src/app/bot/main.py
import asyncio
import logging
import os
from threading import Thread
from aiogram import Bot, Dispatcher

from src.app.bot.handlers import router
from src.app import config
from src.app.logging import setup_logging

logger = logging.getLogger(__name__)


def run_http_server(port: int = 8000) -> None:
    """Запускает простой HTTP сервер для Render Web Service health check."""
    try:
        from http.server import HTTPServer, BaseHTTPRequestHandler
        
        class HealthCheckHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == "/" or self.path == "/health":
                    self.send_response(200)
                    self.send_header("Content-type", "text/plain")
                    self.end_headers()
                    self.wfile.write(b"OK")
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                # Отключаем логирование HTTP запросов
                pass
        
        server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
        logger.info(f"HTTP сервер запущен на порту {port} для Render health check")
        server.serve_forever()
    except Exception as e:
        logger.warning(f"Не удалось запустить HTTP сервер: {e}")


async def main() -> None:
    # Настройка логирования
    setup_logging()
    logger.info("Запуск Telegram-бота...")

    # Запуск HTTP сервера в отдельном потоке (для Render Web Service)
    # Render ожидает, что Web Service слушает на порту из переменной окружения PORT
    port = int(os.getenv("PORT", 8000))
    http_thread = Thread(target=run_http_server, args=(port,), daemon=True)
    http_thread.start()
    logger.info(f"HTTP сервер запущен в фоновом потоке на порту {port}")

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
