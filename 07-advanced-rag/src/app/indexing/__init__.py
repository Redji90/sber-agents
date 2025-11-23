"""Функции для управления процессом индексации данных."""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from langchain_core.documents import Document

from src.app.indexing.loader import load_and_prepare_documents
from src.app.indexing.vector_store import VectorStoreManager, get_vector_store_manager

logger = logging.getLogger(__name__)

_index_lock = asyncio.Lock()


async def _build_vector_store(manager: VectorStoreManager, documents: list[Document]) -> None:
    logger.info("Начинаю создание векторного хранилища для %s чанков. Это может занять несколько минут...", len(documents))
    vector_store = await asyncio.to_thread(manager.build_store_from_documents, documents)
    logger.info("Векторное хранилище создано. Обновляю статус индексации...")
    manager.replace_store(vector_store, chunks=len(documents), documents=documents)


def _format_timestamp(value: datetime | None) -> str:
    if value is None:
        return "—"
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


async def run_full_indexing() -> None:
    """
    Полностью переиндексирует PDF-документы.

    - очищает предыдущие данные;
    - загружает документы и разбивает на чанки;
    - строит новое in-memory векторное хранилище;
    - обновляет статус индексации.
    """
    manager = get_vector_store_manager()

    if _index_lock.locked():
        logger.info("Индексация уже выполняется, повторный запуск отменён.")
        return

    async with _index_lock:
        logger.info("Старт полной переиндексации данных.")
        manager.start_indexing()
        try:
            documents = await asyncio.to_thread(load_and_prepare_documents)
            if not documents:
                manager.reset()
                manager.finish_indexing(chunks=0)
                logger.info("Переиндексация завершена: новые документы не найдены.")
                return

            logger.info("Всего документов для индексации: %s. Начинаю создание эмбеддингов...", len(documents))
            await _build_vector_store(manager, documents)
            logger.info("Переиндексация завершена успешно. Количество чанков: %s.", manager.status.chunks)
        except Exception as exc:
            manager.fail_indexing(message=str(exc))
            logger.exception("Ошибка во время индексации.")


def describe_index_status() -> str:
    status = get_vector_store_manager().status
    if status.updated_at is None and status.state == "idle":
        return "Индекс ещё не создавался."

    parts = [
        f"Статус: {status.state}",
        f"Чанков: {status.chunks}",
        f"Обновлено: {_format_timestamp(status.updated_at)}",
    ]

    if status.state == "running":
        parts.append("Индексация выполняется, дождитесь завершения.")
    if status.error_message:
        parts.append(f"Ошибка: {status.error_message}")

    return "\n".join(parts)
