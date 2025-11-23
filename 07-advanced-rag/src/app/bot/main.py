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


def start_http_server(port: int = 8000) -> Thread:
    """Запускает простой HTTP сервер для Render Web Service health check в отдельном потоке."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    import socket
    
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
    
    def run_server():
        try:
            server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
            server.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            logger.info(f"HTTP сервер запущен на порту {port} для Render health check")
            server.serve_forever()
        except Exception as e:
            logger.error(f"Ошибка HTTP сервера: {e}")
            raise
    
    thread = Thread(target=run_server, daemon=True)
    thread.start()
    return thread


async def main() -> None:
    # Логирование уже настроено в if __name__ == "__main__"
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
    # Настройка логирования ДО запуска сервера
    setup_logging()
    
    # Запуск HTTP сервера СИНХРОННО перед запуском бота
    # Это гарантирует, что порт будет открыт до того, как Render проверит его
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Запуск HTTP сервера на порту {port} для Render health check...")
    http_thread = start_http_server(port)
    
    # Даем серверу время запуститься и привязаться к порту
    import time
    time.sleep(3)  # Увеличиваем задержку для гарантии
    
    # Проверяем, что сервер запустился
    try:
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        if result == 0:
            logger.info(f"✓ HTTP сервер успешно запущен и слушает порт {port}")
        else:
            logger.warning(f"⚠ HTTP сервер может быть не готов на порту {port}")
    except Exception as e:
        logger.warning(f"Не удалось проверить порт {port}: {e}")
    
    # Теперь запускаем бота
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем.")
    except Exception as e:
        logger.exception(f"Произошла непредвиденная ошибка: {e}")
