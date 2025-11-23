#!/usr/bin/env python3
"""Скрипт для проверки подключения к LLM API."""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from langchain_openai import ChatOpenAI
from src.app import config

print("=== Проверка конфигурации LLM ===")
print(f"Base URL: {config.OPENAI_BASE_URL}")
print(f"Model: {config.LLM_MODEL}")
api_key_preview = config.OPENAI_API_KEY[:10] + "..." if config.OPENAI_API_KEY else "None"
print(f"API Key (первые 10 символов): {api_key_preview}")

print("\n=== Тест подключения к LLM API ===")
try:
    llm = ChatOpenAI(
        model=config.LLM_MODEL,
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_BASE_URL,
        temperature=0.2,
        max_retries=2,
        timeout=10.0,
    )
    print("Попытка простого запроса...")
    response = llm.invoke("Привет, ответь одним словом: работает?")
    print(f"✅ Успешно! Ответ: {response.content}")
except Exception as e:
    print(f"❌ Ошибка: {type(e).__name__}: {e}")

