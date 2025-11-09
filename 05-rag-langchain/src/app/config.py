# src/app/config.py
import os
from dotenv import load_dotenv

load_dotenv()  # Загружаем переменные из .env файла


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Переменная окружения {name} не установлена.")
    return value


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"Переменная окружения {name} должна быть целым числом.") from exc


# Обязательные переменные окружения
TELEGRAM_BOT_TOKEN = _get_required_env("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = _get_required_env("OPENAI_API_KEY")

# Необязательные переменные окружения с дефолтными значениями
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.fireworks.ai/inference/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "accounts/fireworks/models/llama-v3p1-8b-instruct")
EMBEDDINGS_MODEL = os.getenv("EMBEDDINGS_MODEL", "accounts/fireworks/models/nomic-embed-text-v1")
SYSTEM_ROLE = os.getenv("SYSTEM_ROLE", "банковский ассистент")
CONTEXT_TURNS = _get_int_env("CONTEXT_TURNS", 8)
RETRIEVER_K = _get_int_env("RETRIEVER_K", 4)
DATA_PATH = os.getenv("DATA_PATH", "@data")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
