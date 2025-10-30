# src/app/config.py
import os
from dotenv import load_dotenv

load_dotenv() # Загружаем переменные из .env файла

# Обязательные переменные окружения
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Валидация обязательных переменных
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("Переменная окружения TELEGRAM_BOT_TOKEN не установлена.")
if not OPENROUTER_API_KEY:
    raise ValueError("Переменная окружения OPENROUTER_API_KEY не установлена.")

# Необязательные переменные окружения с дефолтными значениями
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-5-codex")
SYSTEM_ROLE = os.getenv("SYSTEM_ROLE", "банковский ассистент")
CONTEXT_TURNS = int(os.getenv("CONTEXT_TURNS", "8"))
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
