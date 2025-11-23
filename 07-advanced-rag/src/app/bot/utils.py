"""Утилиты для бота."""
import asyncio
import logging
from typing import Any, Callable, Awaitable

from aiogram.exceptions import TelegramNetworkError
from aiogram.types import Message

logger = logging.getLogger(__name__)


async def send_message_with_retry(
    send_func: Callable[[], Awaitable[Any]],
    max_retries: int = 3,
    retry_delay: float = 2.0,
) -> Any:
    """Отправляет сообщение с автоматическим retry при сетевых ошибках.
    
    Args:
        send_func: Асинхронная функция для отправки сообщения (например, message.answer)
        max_retries: Максимальное количество попыток
        retry_delay: Начальная задержка между попытками в секундах
        
    Returns:
        Результат выполнения send_func
        
    Raises:
        TelegramNetworkError: Если все попытки исчерпаны
    """
    for attempt in range(max_retries):
        try:
            return await send_func()
        except (TelegramNetworkError, Exception) as e:
            error_str = str(e).lower()
            is_network_error = any(keyword in error_str for keyword in [
                "connection", "connector", "ssl", "timeout", "network", "clientconnector"
            ])
            
            if is_network_error and attempt < max_retries - 1:
                delay = retry_delay * (2 ** attempt)  # Экспоненциальная задержка
                logger.warning(
                    "Ошибка сети при отправке сообщения (попытка %s/%s): %s. "
                    "Повторная попытка через %s секунд...",
                    attempt + 1,
                    max_retries,
                    e,
                    delay
                )
                await asyncio.sleep(delay)
                continue
            else:
                # Все попытки исчерпаны или не сетевая ошибка
                if attempt == max_retries - 1:
                    logger.error(
                        "Не удалось отправить сообщение после %s попыток: %s",
                        max_retries,
                        e
                    )
                raise
    # Этот код не должен выполняться, но на всякий случай
    raise TelegramNetworkError("Не удалось отправить сообщение после всех попыток")


async def safe_answer(message: Message, text: str, **kwargs) -> Any:
    """Безопасная отправка сообщения с автоматическим retry.
    
    Args:
        message: Объект сообщения Telegram
        text: Текст сообщения
        **kwargs: Дополнительные параметры для message.answer()
        
    Returns:
        Результат отправки сообщения
    """
    return await send_message_with_retry(
        lambda: message.answer(text, **kwargs)
    )

