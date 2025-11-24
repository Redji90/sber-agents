#!/usr/bin/env python3
"""Скрипт для проверки подключения к LLMost API."""
import os
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Загружаем переменные окружения из .env
try:
    from dotenv import load_dotenv
    env_path = project_root / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        print(f"✅ Загружен .env файл: {env_path}")
    else:
        print(f"⚠️ .env файл не найден: {env_path}")
except ImportError:
    print("⚠️ python-dotenv не установлен, используем переменные окружения системы")

from langchain_openai import ChatOpenAI

# Получаем настройки из переменных окружения
api_key = os.getenv("RAGAS_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
base_url = os.getenv("RAGAS_OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL")
model = os.getenv("RAGAS_LLM_MODEL") or os.getenv("LLM_MODEL", "x-ai/grok-4.1-fast")

# Список возможных URL для LLMost (пробуем по очереди)
# Правильный URL: https://llmost.ru/api/v1 (проверено и работает!)
possible_urls = [
    "https://llmost.ru/api/v1",  # Правильный URL (проверено)
    "https://api.llmost.ru/v1",   # Альтернативный вариант (может не работать)
]

# Если URL не указан или не содержит llmost, пробуем первый вариант
if not base_url or "llmost.ru" not in base_url:
    base_url = possible_urls[0]
    print(f"⚠️ URL не указан, используем: {base_url}")

if not api_key:
    print("❌ Не найден API ключ. Установите RAGAS_OPENAI_API_KEY или OPENAI_API_KEY.")
    sys.exit(1)

print("=== Проверка конфигурации LLMost ===")
print(f"Base URL: {base_url}")
print(f"Model: {model}")
api_key_preview = api_key[:10] + "..." if api_key else "None"
print(f"API Key (первые 10 символов): {api_key_preview}")

print("\n=== Тест подключения к LLMost API ===")

# Пробуем разные URL, если текущий не работает
urls_to_try = [base_url]
if "llmost.ru" in base_url:
    # Добавляем альтернативный URL для тестирования
    if base_url == "https://llmost.ru/api/v1":
        urls_to_try.append("https://api.llmost.ru/v1")
    elif base_url == "https://api.llmost.ru/v1":
        urls_to_try.append("https://llmost.ru/api/v1")

last_error = None
for test_url in urls_to_try:
    print(f"\nПопытка подключения к: {test_url}")
    try:
        llm = ChatOpenAI(
            model=model,
            api_key=api_key,
            base_url=test_url,
            temperature=0.2,
            max_retries=1,  # Уменьшаем retry для быстрой проверки
            timeout=15.0,   # Уменьшаем timeout
        )
        print("Попытка простого запроса...")
        response = llm.invoke("Привет, ответь одним словом: работает?")
        print(f"✅ Успешно! Ответ LLMost: {response.content}")
        print(f"\n✅ Endpoint работает! URL: {test_url}")
        print(f"✅ Модель: {model}")
        print(f"\n💡 Используйте этот URL в .env:")
        print(f"   RAGAS_OPENAI_BASE_URL={test_url}")
        sys.exit(0)
    except Exception as e:
        last_error = e
        error_str = str(e).lower()
        if "connection" in error_str or "timeout" in error_str:
            print(f"❌ Ошибка подключения: {type(e).__name__}")
            if test_url != urls_to_try[-1]:
                print("   Пробуем альтернативный URL...")
                continue
        elif "MODEL_NOT_FOUND" in str(e) or "not found" in error_str:
            print(f"❌ Модель '{model}' не найдена в LLMost")
            print("\n💡 Попробуйте другие модели:")
            print("  - gpt-4")
            print("  - gpt-4-turbo")
            print("  - Проверьте список доступных моделей на https://llmost.ru/")
            sys.exit(1)
        else:
            print(f"❌ Ошибка: {type(e).__name__}: {e}")
            if test_url != urls_to_try[-1]:
                print("   Пробуем альтернативный URL...")
                continue

# Если все URL не сработали
print(f"\n❌ Не удалось подключиться ни к одному из URL")
print(f"Последняя ошибка: {type(last_error).__name__}: {last_error}")
print("\n💡 Возможные причины:")
print("  1. Неправильный URL API (проверьте документацию LLMost)")
print("  2. API ключ неверный или истек")
print("  3. Недостаточно баланса на счету")
print("  4. Проблемы с сетью/блокировка")
print("  5. Сервис LLMost временно недоступен")
print("\n🔍 Попробуйте:")
print("  - Проверить документацию: https://llmost.ru/docs")
print("  - Проверить баланс на сайте LLMost")
print("  - Проверить доступность сайта: https://llmost.ru/")
print("  - Использовать Ollama локально для RAGAS (см. LOCAL_SETUP.md)")
print("\n💡 Альтернатива: используйте Ollama для RAGAS")
print("  RAGAS_OPENAI_BASE_URL=http://localhost:11434/v1")
print("  RAGAS_LLM_MODEL=llama3.1:8b")
sys.exit(1)

