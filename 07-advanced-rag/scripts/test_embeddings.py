#!/usr/bin/env python3
"""Скрипт для проверки работы embeddings."""
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

from src.app.indexing.vector_store import get_embeddings

print("=== Проверка конфигурации Embeddings ===")
from src.app import config
print(f"Embeddings Provider: {config.EMBEDDINGS_PROVIDER}")
print(f"Embeddings Model: {config.EMBEDDINGS_MODEL}")

print("\n=== Тест инициализации Embeddings ===")
try:
    embeddings = get_embeddings()
    print("✅ Embeddings инициализированы")
    
    # Тест эмбеддингов
    test_texts = ["Тестовый текст для проверки эмбеддингов", "Второй тестовый текст"]
    print("Попытка создания эмбеддингов...")
    embeddings_result = embeddings.embed_documents(test_texts)
    print(f"✅ Тест эмбеддингов успешен!")
    print(f"   Количество текстов: {len(test_texts)}")
    print(f"   Количество эмбеддингов: {len(embeddings_result)}")
    print(f"   Размерность эмбеддинга: {len(embeddings_result[0])}")
    
    # Тест одного запроса
    single_embedding = embeddings.embed_query(test_texts[0])
    print(f"✅ Тест embed_query успешен (размерность: {len(single_embedding)})")
    
    print("\n✅ Embeddings готовы к использованию!")
    
except Exception as e:
    print(f"❌ Ошибка при работе с embeddings: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

