#!/usr/bin/env python3
"""Скрипт для переиндексации документов."""
import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.app.indexing import run_full_indexing

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Запускает полную переиндексацию документов."""
    logger.info("🔄 Запуск переиндексации документов...")
    try:
        await run_full_indexing()
        logger.info("✅ Переиндексация завершена успешно!")
    except Exception as exc:
        logger.exception("❌ Ошибка при переиндексации: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

