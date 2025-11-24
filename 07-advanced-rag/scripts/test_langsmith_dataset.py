#!/usr/bin/env python3
"""Скрипт для проверки подключения к LangSmith и загрузки датасета."""
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

from src.app import config
from src.app.evaluation.evaluation import _load_dataset_from_langsmith

print("=== Проверка конфигурации LangSmith ===")
print(f"LANGSMITH_API_KEY: {'установлен' if config.LANGSMITH_API_KEY else 'не установлен'}")
if config.LANGSMITH_API_KEY:
    api_key_preview = config.LANGSMITH_API_KEY[:10] + "..." if len(config.LANGSMITH_API_KEY) > 10 else config.LANGSMITH_API_KEY
    print(f"API Key (первые 10 символов): {api_key_preview}")
print(f"LANGSMITH_PROJECT: {config.LANGSMITH_PROJECT or 'не установлен'}")

if not config.LANGSMITH_API_KEY:
    print("\n❌ LANGSMITH_API_KEY не установлен. Невозможно проверить подключение.")
    sys.exit(1)

print("\n=== Тест подключения к LangSmith ===")
dataset_name = config.LANGSMITH_PROJECT or "06-rag-qa-dataset"
print(f"Попытка загрузить датасет: {dataset_name}")

try:
    dataset = _load_dataset_from_langsmith(dataset_name)
    
    if dataset is None:
        print(f"❌ Не удалось загрузить датасет '{dataset_name}'")
        print("\n💡 Возможные причины:")
        print("  1. Датасет не существует в LangSmith")
        print("  2. Проблемы с подключением к LangSmith API")
        print("  3. Неправильное название датасета")
        sys.exit(1)
    
    print(f"✅ Датасет '{dataset_name}' успешно загружен!")
    print(f"   Количество примеров: {len(dataset)}")
    print(f"   Поля датасета: {list(dataset.column_names)}")
    
    if len(dataset) > 0:
        print("\n=== Первый пример ===")
        first_example = dataset[0]
        print(f"   Question: {first_example.get('question', '')[:100]}...")
        print(f"   Ground truth: {first_example.get('ground_truths', [''])[0][:100] if first_example.get('ground_truths') else ''}...")
        print(f"   Reference: {first_example.get('reference', '')[:100]}...")
    
    print("\n✅ LangSmith подключение работает!")
    print("💡 Теперь можно запускать evaluation через бота командой /evaluate_dataset")
    
except Exception as e:
    print(f"\n❌ Ошибка при проверке LangSmith: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

