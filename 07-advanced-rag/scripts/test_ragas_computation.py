#!/usr/bin/env python3
"""Скрипт для проверки вычисления RAGAS метрик на простом примере."""
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

from datasets import Dataset
from ragas import evaluate
from ragas.metrics import Faithfulness, AnswerRelevancy, AnswerSimilarity
from src.app.evaluation.evaluation import _get_ragas_llm, _get_ragas_embeddings
from src.app import config

print("=== Тест вычисления RAGAS метрик на простом примере ===\n")

# Создаем простой тестовый датасет
test_data = {
    "question": ["Что такое банк?"],
    "answer": ["Банк - это финансовое учреждение, которое предоставляет различные финансовые услуги."],
    "contexts": [["Банк - это финансовое учреждение, которое принимает вклады и выдает кредиты."]],
    "ground_truths": [["Банк - это финансовое учреждение."]],
    "reference": ["Банк - это финансовое учреждение."],  # Требуется для AnswerSimilarity
}

dataset = Dataset.from_dict(test_data)
print("✅ Тестовый датасет создан:")
print(f"   Question: {test_data['question'][0]}")
print(f"   Answer: {test_data['answer'][0][:50]}...")
print(f"   Context: {test_data['contexts'][0][0][:50]}...")

print("\n=== Инициализация RAGAS компонентов ===")
try:
    llm = _get_ragas_llm()
    print(f"✅ RAGAS LLM инициализирован: {config.RAGAS_LLM_MODEL or config.LLM_MODEL}")
    
    embeddings = _get_ragas_embeddings()
    print(f"✅ RAGAS Embeddings инициализированы: {config.RAGAS_EMBEDDING_MODEL}")
except Exception as e:
    print(f"❌ Ошибка инициализации: {e}")
    sys.exit(1)

print("\n=== Вычисление метрик ===")
try:
    from ragas import RunConfig
    
    # Используем только простые метрики для теста
    metrics = [
        Faithfulness(llm=llm),
        AnswerRelevancy(llm=llm, embeddings=embeddings),
        AnswerSimilarity(embeddings=embeddings),
    ]
    
    # RunConfig может не поддерживать sleep_time, используем только max_workers
    try:
        run_config = RunConfig(max_workers=1)
        print("Запуск evaluation с RunConfig(max_workers=1)...")
        result = evaluate(dataset=dataset, metrics=metrics, run_config=run_config)
    except TypeError:
        # Если RunConfig не поддерживает параметры, запускаем без него
        print("Запуск evaluation без RunConfig...")
        result = evaluate(dataset=dataset, metrics=metrics)
    
    print("\n=== Результаты ===")
    print(f"Faithfulness: {getattr(result, 'faithfulness', 'N/A')}")
    print(f"Answer Relevancy: {getattr(result, 'answer_relevancy', 'N/A')}")
    print(f"Answer Similarity: {getattr(result, 'answer_similarity', 'N/A')}")
    
    # Проверяем scores
    if hasattr(result, 'scores'):
        print(f"\nScores: {result.scores}")
        if isinstance(result.scores, list) and len(result.scores) > 0:
            first_score = result.scores[0]
            print(f"Первый score: {first_score}")
            print(f"  faithfulness: {first_score.get('faithfulness', 'N/A')}")
            print(f"  answer_relevancy: {first_score.get('answer_relevancy', 'N/A')}")
            print(f"  answer_similarity: {first_score.get('answer_similarity', 'N/A')}")
    
    print("\n✅ Тест завершен успешно!")
    
except Exception as e:
    print(f"\n❌ Ошибка при вычислении метрик: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

