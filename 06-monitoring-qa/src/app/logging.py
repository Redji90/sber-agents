# src/app/logging.py
import logging
from src.app import config # Импортируем конфиг для LOG_LEVEL

def setup_logging():
    logging.basicConfig(
        level=config.LOG_LEVEL,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )
    logging.getLogger(__name__).info("Логирование настроено.")
