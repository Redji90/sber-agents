#!/usr/bin/env python3
"""Скрипт для прямого запуска evaluation без Telegram бота."""
import asyncio
import logging
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.app import config
from src.app.evaluation.evaluation import evaluate_rag_pipeline_with_feedback
from src.app.indexing.vector_store import get_vector_store_manager

# Настраиваем логирование
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    """Запускает evaluation RAG pipeline."""
    # Проверяем наличие LangSmith API ключа
    if not config.LANGSMITH_API_KEY:
        logger.error("❌ LangSmith API ключ не установлен.")
        logger.error("Установите переменную окружения LANGSMITH_API_KEY для использования evaluation.")
        sys.exit(1)

    # Проверяем наличие индекса
    manager = get_vector_store_manager()
    status = manager.status

    if status.chunks == 0:
        logger.error("❌ Индекс пуст. Для evaluation нужен индекс документов.")
        logger.error("Запустите /index в Telegram боте и дождитесь завершения.")
        sys.exit(1)

    # Название датасета по умолчанию
    dataset_name = config.LANGSMITH_PROJECT or "06-rag-qa-dataset"

    logger.info("🔄 Запускаю evaluation датасета '%s'...", dataset_name)
    logger.info("Текущая конфигурация:")
    logger.info("  RAG_MODE: %s", config.RAG_MODE)
    logger.info("  SEMANTIC_K: %s", config.SEMANTIC_K)
    logger.info("  EMBEDDINGS_PROVIDER: %s", config.EMBEDDINGS_PROVIDER)
    logger.info("  EMBEDDINGS_MODEL: %s", config.EMBEDDINGS_MODEL)
    logger.info("  LLM_MODEL: %s", config.LLM_MODEL)
    logger.info("  EVALUATION_MAX_CONCURRENT: %s", config.EVALUATION_MAX_CONCURRENT)
    logger.info("  EVALUATION_DELAY_BETWEEN_REQUESTS: %s", config.EVALUATION_DELAY_BETWEEN_REQUESTS)

    try:
        # Запускаем evaluation
        retriever = manager.get_retriever()
        result = evaluate_rag_pipeline_with_feedback(
            dataset_name=dataset_name,
            retriever=retriever,
            upload_feedback=True,
        )

        # Результат может быть словарем метрик или кортежем (метрики, количество примеров)
        if isinstance(result, tuple):
            metrics, examples_count = result
        else:
            metrics = result
            examples_count = "?"

        # Выводим результаты
        print("\n" + "=" * 60)
        print("✅ Evaluation завершен!")
        print("=" * 60)
        print(f"\n📊 Датасет: {dataset_name}")
        print(f"📝 Примеров обработано: {examples_count}\n")

        print("🎯 RAGAS Метрики:")
        
        # Словарь соответствия английских названий метрик русским названиям и цветам
        metric_names = {
            "faithfulness": ("Обоснованность (нет галлюцинаций)", "🔴" if metrics.get("faithfulness", 0) == 0.0 else "🟢"),
            "answer_relevancy": ("Релевантность ответа", "🔴" if metrics.get("answer_relevancy", 0) == 0.0 else "🟢"),
            "answer_correctness": ("Правильность ответа", "🟡" if 0.3 <= metrics.get("answer_correctness", 0) < 0.7 else ("🟢" if metrics.get("answer_correctness", 0) >= 0.7 else "🔴")),
            "answer_similarity": ("Похожесть на эталон", "🟢" if metrics.get("answer_similarity", 0) >= 0.7 else "🟡"),
            "context_recall": ("Полнота контекста", "🟡" if 0.3 <= metrics.get("context_recall", 0) < 0.7 else ("🟢" if metrics.get("context_recall", 0) >= 0.7 else "🔴")),
            "context_precision": ("Точность поиска", "🔴" if metrics.get("context_precision", 0) == 0.0 else "🟢"),
        }

        for metric_key, (metric_name, emoji) in metric_names.items():
            value = metrics.get(metric_key, 0.0)
            print(f"{emoji} {metric_name}: {value:.3f}")

        print("\n💡 Результаты загружены в LangSmith как feedback")
        print("=" * 60)

        logger.info("Evaluation завершён успешно. Метрики: %s", metrics)

    except Exception as exc:
        logger.exception("❌ Произошла ошибка при выполнении evaluation: %s", exc)
        sys.exit(1)


if __name__ == "__main__":
    main()

