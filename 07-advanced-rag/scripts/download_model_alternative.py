#!/usr/bin/env python3
"""Альтернативный скрипт для загрузки модели через huggingface-cli или wget."""
import sys
import subprocess
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.app import config
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def download_with_huggingface_cli(model_name: str, cache_folder: str | None = None):
    """Загружает модель через huggingface-cli (более надежный способ)."""
    try:
        cache_dir = cache_folder or config.HUGGINGFACE_CACHE_FOLDER
        
        if cache_dir:
            cache_path = Path(cache_dir).expanduser().resolve()
            cache_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Используется кэш: {cache_path}")
        else:
            cache_path = None
            logger.info("Используется дефолтный кэш HuggingFace")
        
        # Команда для загрузки
        cmd = ["huggingface-cli", "download", model_name]
        
        if cache_path:
            cmd.extend(["--cache-dir", str(cache_path)])
        
        logger.info(f"Загрузка модели {model_name} через huggingface-cli...")
        logger.info(f"Команда: {' '.join(cmd)}")
        logger.info("Это может занять длительное время для больших моделей...")
        
        # Запускаем команду
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=False,  # Показываем вывод в реальном времени
            text=True
        )
        
        logger.info(f"✅ Модель {model_name} успешно загружена!")
        if cache_path:
            logger.info(f"Кэш находится в: {cache_path}")
        
        return True
        
    except FileNotFoundError:
        logger.error("huggingface-cli не найден. Установите: uv pip install 'huggingface_hub[cli]'")
        return False
    except subprocess.CalledProcessError as exc:
        logger.error(f"Ошибка при загрузке через huggingface-cli: {exc}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Альтернативная загрузка модели HuggingFace через CLI")
    parser.add_argument(
        "--cache-folder",
        type=str,
        default=None,
        help="Путь к папке кэша"
    )
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Имя модели (по умолчанию из конфигурации)"
    )
    
    args = parser.parse_args()
    
    model_name = args.model or config.EMBEDDINGS_MODEL
    
    logger.info(f"Загрузка модели: {model_name}")
    if args.cache_folder:
        logger.info(f"Кэш: {args.cache_folder}")
    
    success = download_with_huggingface_cli(model_name, args.cache_folder)
    
    if not success:
        logger.error("\n💡 Альтернативные способы загрузки:")
        logger.error("1. Используйте более легкую модель для тестирования:")
        logger.error("   EMBEDDINGS_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
        logger.error("2. Попробуйте использовать VPN или другое интернет-соединение")
        logger.error("3. Загрузите модель вручную с сайта huggingface.co")
        sys.exit(1)

