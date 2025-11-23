#!/usr/bin/env python3
"""Скрипт для предварительной загрузки модели HuggingFace."""
import os
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.app import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_huggingface_model(model_name: str, device: str = "cpu", cache_folder: str | None = None, max_retries: int = 5):
    """Загружает модель HuggingFace в кэш с повторными попытками при ошибках.
    
    Args:
        model_name: Имя модели HuggingFace
        device: Устройство (cpu/cuda)
        cache_folder: Путь к папке кэша (если None, используется переменная окружения HF_HOME или дефолтный кэш)
        max_retries: Максимальное количество попыток при ошибках загрузки
    """
    try:
        from sentence_transformers import SentenceTransformer
        import time
        
        # Настраиваем кэш HuggingFace
        if cache_folder:
            cache_path = Path(cache_folder).expanduser().resolve()
            cache_path.mkdir(parents=True, exist_ok=True)
            os.environ["HF_HOME"] = str(cache_path)
            os.environ["TRANSFORMERS_CACHE"] = str(cache_path / "transformers")
            os.environ["HF_DATASETS_CACHE"] = str(cache_path / "datasets")
            logger.info(f"Используется кэш HuggingFace: {cache_path}")
        elif os.getenv("HF_HOME"):
            logger.info(f"Используется кэш HuggingFace из переменной окружения HF_HOME: {os.getenv('HF_HOME')}")
        else:
            # Пробуем использовать диск D, E или другой, если C недоступен
            default_cache = None
            for drive in ["D", "E", "F"]:
                test_path = Path(f"{drive}:\\huggingface_cache")
                try:
                    test_path.mkdir(parents=True, exist_ok=True)
                    default_cache = test_path
                    logger.info(f"Автоматически выбран кэш на диске {drive}: {default_cache}")
                    break
                except (OSError, PermissionError):
                    continue
            
            if default_cache:
                os.environ["HF_HOME"] = str(default_cache)
                os.environ["TRANSFORMERS_CACHE"] = str(default_cache / "transformers")
                os.environ["HF_DATASETS_CACHE"] = str(default_cache / "datasets")
            else:
                logger.warning("Не удалось создать кэш на альтернативном диске, используется дефолтный кэш")
        
        # Увеличиваем таймауты для загрузки больших моделей
        os.environ["HF_HUB_DOWNLOAD_TIMEOUT"] = "1800"  # 30 минут
        os.environ["HF_HUB_DOWNLOAD_TIMEOUT_STREAM"] = "1800"  # 30 минут для потоковой загрузки
        # Увеличиваем таймаут для requests
        import requests
        requests.adapters.DEFAULT_TIMEOUT = 1800  # 30 минут
        
        logger.info(f"Загрузка модели {model_name} на устройство {device}...")
        logger.info("Это может занять несколько минут при первом запуске...")
        logger.info("При обрыве соединения загрузка будет повторяться автоматически...")
        
        # Загружаем модель с повторными попытками
        kwargs = {
            "model_name_or_path": model_name,
            "device": device,
        }
        
        if cache_folder:
            kwargs["cache_folder"] = str(cache_path)
        
        last_exception = None
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"Попытка {attempt} из {max_retries}...")
                model = SentenceTransformer(**kwargs)
                
                logger.info(f"✅ Модель {model_name} успешно загружена и сохранена в кэш!")
                logger.info(f"Размер модели: {len(model.get_sentence_embedding_dimension())} измерений")
                logger.info(f"Кэш находится в: {os.getenv('HF_HOME', 'дефолтный кэш HuggingFace')}")
                
                return model
            except (ConnectionError, TimeoutError, Exception) as exc:
                last_exception = exc
                error_msg = str(exc)
                
                # Проверяем, является ли это ошибкой сети/таймаута
                if any(keyword in error_msg.lower() for keyword in ["timeout", "connection", "read timed out", "chunkedencoding"]):
                    if attempt < max_retries:
                        wait_time = min(attempt * 10, 60)  # Увеличиваем время ожидания до 60 секунд
                        logger.warning(
                            f"Ошибка сети при загрузке (попытка {attempt}/{max_retries}): {error_msg[:100]}"
                        )
                        logger.info(f"Ожидание {wait_time} секунд перед повторной попыткой...")
                        time.sleep(wait_time)
                        continue
                    else:
                        logger.error(f"Не удалось загрузить модель после {max_retries} попыток")
                        raise
                else:
                    # Другая ошибка - не повторяем
                    raise
        
        # Если дошли сюда, все попытки исчерпаны
        raise last_exception
        
    except ImportError:
        logger.error("sentence-transformers не установлен. Установите: uv pip install sentence-transformers")
        sys.exit(1)
    except Exception as exc:
        logger.exception(f"Ошибка при загрузке модели {model_name}: {exc}")
        logger.error("\n💡 Рекомендации:")
        logger.error("1. Проверьте интернет-соединение")
        logger.error("2. Попробуйте использовать VPN, если есть проблемы с доступом к HuggingFace")
        logger.error("3. Попробуйте загрузить модель вручную через huggingface-cli:")
        logger.error(f"   huggingface-cli download {model_name}")
        logger.error("4. Или используйте более легкую модель для тестирования")
        sys.exit(1)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Загрузка модели HuggingFace")
    parser.add_argument(
        "--cache-folder",
        type=str,
        default=None,
        help="Путь к папке кэша (например, D:\\huggingface_cache). Если не указан, используется HF_HOME или автоматический выбор диска"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Имя модели (по умолчанию из конфигурации)"
    )
    parser.add_argument(
        "--device",
        type=str,
        default=None,
        help="Устройство: cpu или cuda (по умолчанию из конфигурации)"
    )
    parser.add_argument(
        "--max-retries",
        type=int,
        default=5,
        help="Максимальное количество попыток при ошибках загрузки (по умолчанию: 5)"
    )
    
    args = parser.parse_args()
    
    # Определяем модель из конфигурации или аргументов
    if args.model:
        model_name = args.model
    else:
        if config.EMBEDDINGS_PROVIDER.lower() != "huggingface":
            logger.warning(
                f"Текущий провайдер эмбеддингов: {config.EMBEDDINGS_PROVIDER}. "
                "Этот скрипт предназначен для загрузки HuggingFace моделей."
            )
        model_name = config.EMBEDDINGS_MODEL
    
    device = args.device or config.HUGGINGFACE_DEVICE
    cache_folder = args.cache_folder or config.HUGGINGFACE_CACHE_FOLDER
    
    logger.info(f"Загрузка модели: {model_name}")
    logger.info(f"Устройство: {device}")
    logger.info(f"Максимум попыток: {args.max_retries}")
    if cache_folder:
        logger.info(f"Кэш: {cache_folder}")
    else:
        logger.info("Кэш: будет выбран автоматически или из переменной окружения HF_HOME")
    
    download_huggingface_model(model_name, device, cache_folder, args.max_retries)

