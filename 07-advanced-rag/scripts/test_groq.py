#!/usr/bin/env python3
"""
Простой скрипт для проверки доступа к Groq API.

Использует OpenAI-совместимый клиент и минимальный запрос к модели.
Переменные окружения:
    GROQ_API_KEY (или OPENAI_API_KEY)  — API ключ Groq
    GROQ_BASE_URL (опционально)        — базовый URL (по умолчанию https://api.groq.com/openai/v1)
    GROQ_MODEL (опционально)           — название модели (по умолчанию llama-3.1-8b-instant)
"""
from __future__ import annotations

import os
import sys

from openai import OpenAI


def main() -> None:
    base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    api_key = os.getenv("GROQ_API_KEY") or os.getenv("OPENAI_API_KEY")
    model = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

    if not api_key:
        print("❌ Не найден API ключ. Установите GROQ_API_KEY или OPENAI_API_KEY.")
        sys.exit(1)

    print("=== Проверка доступа к Groq ===")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    api_key_preview = api_key[:10] + "..." if len(api_key) > 10 else api_key
    print(f"API Key (первые символы): {api_key_preview}")

    client = OpenAI(api_key=api_key, base_url=base_url, timeout=15)

    try:
        print("\nОтправка тестового запроса...")
        response = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "user",
                    "content": "Ответь одним словом 'Работает', если видишь это сообщение.",
                }
            ],
            temperature=0.1,
            max_tokens=5,
        )
        content = response.choices[0].message.content if response.choices else ""
        print(f"✅ Успешно! Ответ Groq: {content!r}")
    except Exception as exc:  # noqa: BLE001
        print(f"❌ Ошибка при обращении к Groq: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()


