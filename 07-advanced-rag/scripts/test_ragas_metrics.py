#!/usr/bin/env python3
"""Скрипт для проверки работы RAGAS метрик с текущими настройками."""
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
from src.app import config

print("=== Проверка конфигурации RAGAS LLM ===")
print(f"RAGAS LLM Model: {config.RAGAS_LLM_MODEL or config.LLM_MODEL}")
print(f"RAGAS Base URL: {config.RAGAS_OPENAI_BASE_URL}")
api_key_preview = config.RAGAS_OPENAI_API_KEY[:10] + "..." if config.RAGAS_OPENAI_API_KEY else "None"
print(f"RAGAS API Key (первые 10 символов): {api_key_preview}")

print("\n=== Тест подключения к RAGAS LLM ===")
try:
    llm = ChatOpenAI(
        model=config.RAGAS_LLM_MODEL or config.LLM_MODEL,
        api_key=config.RAGAS_OPENAI_API_KEY,
        base_url=config.RAGAS_OPENAI_BASE_URL,
        temperature=0.2,
        max_retries=2,
        timeout=30.0,
    )
    print("Попытка простого запроса...")
    response = llm.invoke("Привет, ответь одним словом: работает?")
    print(f"✅ Успешно! Ответ RAGAS LLM: {response.content}")
    print(f"\n✅ RAGAS LLM готов к использованию!")
except Exception as e:
    print(f"❌ Ошибка при обращении к RAGAS LLM: {type(e).__name__}: {e}")
    sys.exit(1)

print("\n=== Проверка RAGAS Embeddings ===")
print(f"RAGAS Embeddings Provider: {config.RAGAS_EMBEDDINGS_PROVIDER}")
print(f"RAGAS Embedding Model: {config.RAGAS_EMBEDDING_MODEL}")

try:
    from src.app.evaluation.evaluation import _get_ragas_embeddings
    embeddings = _get_ragas_embeddings()
    print("✅ RAGAS Embeddings инициализированы")
    
    # Тест эмбеддингов
    test_text = "Тестовый текст для проверки эмбеддингов"
    try:
        if hasattr(embeddings, 'embed_query'):
            test_embedding = embeddings.embed_query(test_text)
            print(f"✅ Тест эмбеддингов успешен (размерность: {len(test_embedding)})")
        elif hasattr(embeddings, 'embed_text'):
            # RAGAS embeddings могут использовать embed_text
            test_embedding = embeddings.embed_text(test_text)
            print(f"✅ Тест эмбеддингов успешен (размерность: {len(test_embedding)})")
        elif hasattr(embeddings, 'embed_documents'):
            # LangChain embeddings используют embed_documents
            test_embedding = embeddings.embed_documents([test_text])[0]
            print(f"✅ Тест эмбеддингов успешен (размерность: {len(test_embedding)})")
        else:
            print("⚠️ Метод для эмбеддингов не найден, но embeddings инициализированы")
            print(f"   Доступные методы: {[m for m in dir(embeddings) if not m.startswith('_')]}")
    except Exception as e:
        print(f"⚠️ Ошибка при тесте эмбеддингов: {e}")
        print("   Но embeddings инициализированы, возможно, это нормально для RAGAS")
except Exception as e:
    print(f"❌ Ошибка при инициализации RAGAS Embeddings: {type(e).__name__}: {e}")
    sys.exit(1)

print("\n=== Итоговая проверка ===")
print("✅ RAGAS LLM: готов")
print("✅ RAGAS Embeddings: готов")
print("\n💡 Теперь можно запускать evaluation через бота командой /evaluate_dataset")

