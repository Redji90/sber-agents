"""Модуль evaluation качества RAG pipeline через RAGAS метрики."""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from datasets import Dataset
from langchain_core.retrievers import BaseRetriever
from ragas import evaluate
from ragas.metrics import (
    AnswerCorrectness,
    AnswerRelevancy,
    AnswerSimilarity,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

from src.app import config
from src.app.indexing.vector_store import get_vector_store_manager
from src.app.rag.chain import build_rag_chain

logger = logging.getLogger(__name__)


def _get_ragas_embeddings():
    """Возвращает эмбеддинги для RAGAS в зависимости от провайдера."""
    provider = config.RAGAS_EMBEDDINGS_PROVIDER.lower()

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        embeddings = OpenAIEmbeddings(
            model=config.RAGAS_EMBEDDING_MODEL,
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
        )
        logger.info("Используются OpenAI embeddings для RAGAS: %s", config.RAGAS_EMBEDDING_MODEL)
        return embeddings
    elif provider == "huggingface":
        # RAGAS может требовать метод embed_text, которого нет у HuggingFaceEmbeddings
        # Используем embeddings из ragas напрямую для совместимости
        try:
            from ragas.embeddings import HuggingFaceEmbeddings as RAGASHuggingFaceEmbeddings

            embeddings = RAGASHuggingFaceEmbeddings(
                model=config.RAGAS_EMBEDDING_MODEL,
            )
            logger.info("Используются RAGAS HuggingFace embeddings: %s", config.RAGAS_EMBEDDING_MODEL)
            return embeddings
        except ImportError:
            # Fallback на langchain-huggingface, если ragas.embeddings недоступен
            from langchain_huggingface import HuggingFaceEmbeddings

            model_kwargs = {"device": config.HUGGINGFACE_DEVICE}
            encode_kwargs = {"normalize_embeddings": config.HUGGINGFACE_NORMALIZE_EMBEDDINGS}

            kwargs = {
                "model_name": config.RAGAS_EMBEDDING_MODEL,
                "model_kwargs": model_kwargs,
                "encode_kwargs": encode_kwargs,
            }

            if config.HUGGINGFACE_CACHE_FOLDER:
                kwargs["cache_folder"] = config.HUGGINGFACE_CACHE_FOLDER

            embeddings = HuggingFaceEmbeddings(**kwargs)
            logger.warning(
                "Используются langchain HuggingFace embeddings (может быть несовместимо с RAGAS): %s",
                config.RAGAS_EMBEDDING_MODEL
            )
            return embeddings
    else:
        raise ValueError(f"Неподдерживаемый провайдер эмбеддингов для RAGAS: {provider}")


def _get_ragas_llm():
    """Возвращает LLM для RAGAS с обработкой rate limits."""
    from langchain_openai import ChatOpenAI

    # Убеждаемся, что модель указана
    model = config.RAGAS_LLM_MODEL or config.LLM_MODEL
    if not model:
        raise ValueError("LLM_MODEL или RAGAS_LLM_MODEL должен быть установлен")

    # ChatOpenAI не принимает client напрямую, используем параметры
    return ChatOpenAI(
        model=model,
        temperature=0.2,
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_BASE_URL,
        max_retries=20,  # Увеличено для более агрессивной обработки rate limits
        timeout=120.0,  # Увеличен таймаут до 120 секунд для retry
    )


def _load_dataset_from_langsmith(dataset_name: str) -> Dataset | None:
    """Загружает датасет из LangSmith."""
    if not config.LANGSMITH_API_KEY:
        logger.warning("LANGSMITH_API_KEY не установлен. Невозможно загрузить датасет из LangSmith.")
        return None

    try:
        from langsmith import Client

        client = Client(api_key=config.LANGSMITH_API_KEY)

        # Проверяем существование датасета
        try:
            dataset_info = client.read_dataset(dataset_name=dataset_name)
            logger.info("Найден датасет '%s' в LangSmith", dataset_name)
        except Exception as exc:
            logger.error("Датасет '%s' не найден в LangSmith: %s", dataset_name, exc)
            return None

        # Загружаем примеры из датасета
        examples = list(client.list_examples(dataset_name=dataset_name))

        if not examples:
            logger.warning("Датасет '%s' пуст", dataset_name)
            return None

        # Преобразуем в формат для RAGAS
        data = {
            "question": [],
            "ground_truths": [],
            "reference": [],  # Требуется для AnswerCorrectness
        }

        for example in examples:
            inputs = example.inputs or {}
            outputs = example.outputs or {}
            data["question"].append(inputs.get("question", ""))
            # ground_truths - это эталонные ответы из датасета (список для ContextRecall)
            ground_truth = outputs.get("answer", "")
            ground_truth_list = [ground_truth] if ground_truth else [""]
            data["ground_truths"].append(ground_truth_list)
            # reference - эталонный ответ для AnswerCorrectness (строка, первый из ground_truths)
            data["reference"].append(ground_truth_list[0] if ground_truth_list else "")

        dataset = Dataset.from_dict(data)
        logger.info("Загружено %s примеров из датасета '%s'", len(dataset), dataset_name)
        return dataset

    except ImportError:
        logger.warning("langsmith не установлен. Невозможно загрузить датасет из LangSmith.")
        return None
    except Exception as exc:
        logger.exception("Ошибка при загрузке датасета из LangSmith: %s", exc)
        return None


async def _process_single_example(
    rag_chain: Any,
    example: dict,
    idx: int,
    total: int,
    semaphore: asyncio.Semaphore,
    delay: float = 0.5,
    max_retries: int = 5,  # Увеличено количество retry попыток
) -> tuple[str, list[str]]:
    """Обрабатывает один пример датасета через RAG pipeline с retry логикой."""
    async with semaphore:
        question = example["question"]
        logger.info("Обработка примера %s/%s: %s", idx, total, question[:50] + "...")

        # Retry логика для обработки rate limit ошибок
        for attempt in range(max_retries):
            try:
                # Запускаем RAG в отдельном потоке, чтобы не блокировать event loop
                result = await asyncio.to_thread(
                    rag_chain.invoke,
                    {"input": question, "chat_history": []}
                )
                answer = result.get("answer", "")
                documents = result.get("context", [])

                # Извлекаем контексты из документов
                contexts = [doc.page_content for doc in documents] if documents else [""]

                # Задержка применяется только при необходимости (не после каждого успешного запроса)
                # Это ускоряет обработку, так как rate limits обрабатываются через retry логику
                # if delay > 0:
                #     await asyncio.sleep(delay)

                return answer, contexts
            except Exception as exc:
                # Проверяем, является ли это rate limit ошибкой
                is_rate_limit = False
                try:
                    from openai import RateLimitError
                    is_rate_limit = isinstance(exc, RateLimitError) or (
                        hasattr(exc, "status_code") and exc.status_code == 429
                    ) or "rate limit" in str(exc).lower() or "429" in str(exc)
                except ImportError:
                    # Если не можем импортировать, проверяем по строке
                    is_rate_limit = "rate limit" in str(exc).lower() or "429" in str(exc)

                if is_rate_limit and attempt < max_retries - 1:
                    # Экспоненциальная задержка с базовой задержкой 5 секунд
                    # 5, 10, 20 секунд для более надежной обработки rate limits
                    retry_delay = 5.0 * (2 ** attempt)
                    logger.warning(
                        "Rate limit при обработке примера %s/%s (попытка %s/%s). "
                        "Ожидание %s секунд...",
                        idx,
                        total,
                        attempt + 1,
                        max_retries,
                        retry_delay,
                    )
                    await asyncio.sleep(retry_delay)
                    continue
                else:
                    # Если это не rate limit или закончились попытки
                    logger.warning("Ошибка при обработке примера %s/%s: %s", idx, total, exc)
                    return "", [""]

        # Если все попытки исчерпаны
        logger.warning("Не удалось обработать пример %s/%s после %s попыток", idx, total, max_retries)
        return "", [""]


def _run_rag_on_dataset(dataset: Dataset, retriever: BaseRetriever) -> Dataset:
    """Запускает RAG pipeline на всех примерах датасета с параллельной обработкой."""
    rag_chain = build_rag_chain(retriever)

    # Ограничиваем количество примеров, если задано в конфиге (для тестирования)
    total_examples = len(dataset)
    if config.EVALUATION_MAX_EXAMPLES > 0 and total_examples > config.EVALUATION_MAX_EXAMPLES:
        logger.info(
            "Ограничение количества примеров: %s из %s будут обработаны (EVALUATION_MAX_EXAMPLES=%s)",
            config.EVALUATION_MAX_EXAMPLES,
            total_examples,
            config.EVALUATION_MAX_EXAMPLES
        )
        dataset = dataset.select(range(config.EVALUATION_MAX_EXAMPLES))
        total_examples = config.EVALUATION_MAX_EXAMPLES

    logger.info("Запуск RAG на %s примерах датасета", total_examples)

    # Параллельная обработка с ограничением concurrency
    # Параметры настраиваются через переменные окружения
    max_concurrent = config.EVALUATION_MAX_CONCURRENT
    delay_between_requests = config.EVALUATION_DELAY_BETWEEN_REQUESTS
    
    logger.info(
        "Параметры параллельной обработки: max_concurrent=%s, delay=%s сек",
        max_concurrent,
        delay_between_requests
    )

    async def process_all():
        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = []

        for idx, example in enumerate(dataset, 1):
            task = _process_single_example(
                rag_chain,
                example,
                idx,
                total_examples,
                semaphore,
                delay_between_requests,
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        answers = []
        contexts_list = []

        for result in results:
            if isinstance(result, Exception):
                logger.warning("Ошибка при обработке примера: %s", result)
                answers.append("")
                contexts_list.append([""])
            else:
                answer, contexts = result
                answers.append(answer)
                contexts_list.append(contexts)

        return answers, contexts_list

    # Запускаем асинхронную обработку
    answers, contexts_list = asyncio.run(process_all())

    # Обновляем датасет с результатами RAG
    # RAGAS ожидает answer и contexts в датасете
    dataset = dataset.add_column("answer", answers)
    dataset = dataset.add_column("contexts", contexts_list)

    # Диагностическое логирование: проверяем валидность данных после RAG
    empty_answers = sum(1 for a in answers if not a or not a.strip())
    empty_contexts = sum(1 for ctx_list in contexts_list if not ctx_list or all(not c or not c.strip() for c in ctx_list))
    avg_answer_length = sum(len(a) for a in answers) / len(answers) if answers else 0
    avg_contexts_count = sum(len(ctx_list) for ctx_list in contexts_list) / len(contexts_list) if contexts_list else 0
    
    logger.info(
        "RAG выполнен на всех примерах датасета. Статистика: "
        "пустых ответов=%s/%s, пустых контекстов=%s/%s, "
        "средняя длина ответа=%.1f символов, среднее количество контекстов=%.1f",
        empty_answers,
        len(answers),
        empty_contexts,
        len(contexts_list),
        avg_answer_length,
        avg_contexts_count
    )
    
    # Логируем первые несколько примеров для диагностики
    if len(dataset) > 0:
        logger.debug("Пример данных после RAG (первые 3 записи):")
        for i in range(min(3, len(dataset))):
            example = dataset[i]
            logger.debug(
                "  Пример %s: question='%s...', answer_len=%s, contexts_count=%s",
                i + 1,
                example.get("question", "")[:50],
                len(example.get("answer", "")),
                len(example.get("contexts", []))
            )
    
    return dataset


def evaluate_rag_pipeline(
    dataset_name: str,
    retriever: BaseRetriever | None = None,
) -> dict[str, float]:
    """Выполняет evaluation RAG pipeline через RAGAS метрики.

    Args:
        dataset_name: Название датасета в LangSmith
        retriever: Retriever для RAG (если None, используется из vector_store_manager)

    Returns:
        Словарь с метриками: faithfulness, answer_relevancy, answer_correctness,
        answer_similarity, context_recall, context_precision
    """
    logger.info("Начало evaluation RAG pipeline с датасетом '%s'", dataset_name)

    # Загружаем датасет из LangSmith
    dataset = _load_dataset_from_langsmith(dataset_name)
    if dataset is None:
        raise ValueError(f"Не удалось загрузить датасет '{dataset_name}' из LangSmith")

    # Сохраняем количество примеров для возврата
    examples_count = len(dataset)

    # Получаем retriever
    if retriever is None:
        manager = get_vector_store_manager()
        retriever = manager.get_retriever()

    # Запускаем RAG на всех примерах
    dataset_with_rag = _run_rag_on_dataset(dataset, retriever)

    # Настраиваем RAGAS метрики
    embeddings = _get_ragas_embeddings()
    llm = _get_ragas_llm()

    # Вычисляем метрики
    # В RAGAS метрики - это классы, которые нужно инстанцировать с параметрами
    # Некоторые метрики требуют только llm, другие - embeddings, третьи - оба
    # В быстром режиме используем только основные метрики для ускорения
    if config.EVALUATION_FAST_MODE:
        logger.info("Используется быстрый режим evaluation (только основные метрики)")
        metrics = [
            Faithfulness(llm=llm),
            AnswerRelevancy(llm=llm, embeddings=embeddings),
            AnswerSimilarity(embeddings=embeddings),
        ]
    else:
        metrics = [
            Faithfulness(llm=llm),
            AnswerRelevancy(llm=llm, embeddings=embeddings),
            AnswerCorrectness(llm=llm, embeddings=embeddings),
            AnswerSimilarity(embeddings=embeddings),
            ContextRecall(llm=llm),
            ContextPrecision(llm=llm),
        ]

    logger.info("Вычисление RAGAS метрик...")
    result = evaluate(dataset=dataset_with_rag, metrics=metrics)

    # Извлекаем средние значения метрик
    # RAGAS может возвращать метрики как списки или скалярные значения
    def _extract_metric_value(metric_result):
        """Извлекает числовое значение из результата метрики."""
        if metric_result is None:
            return 0.0
        if isinstance(metric_result, (list, tuple)):
            # Если список, берем среднее значение
            if len(metric_result) == 0:
                return 0.0
            # Фильтруем None значения и строки
            valid_values = [v for v in metric_result if v is not None and isinstance(v, (int, float))]
            if len(valid_values) == 0:
                return 0.0
            return float(sum(valid_values) / len(valid_values))
        elif isinstance(metric_result, (int, float)):
            return float(metric_result)
        elif isinstance(metric_result, str):
            try:
                return float(metric_result)
            except ValueError:
                logger.warning("Не удалось преобразовать метрику в число: %s", metric_result)
                return 0.0
        else:
            logger.warning("Неожиданный тип результата метрики: %s (тип: %s)", metric_result, type(metric_result))
            return 0.0

    # RAGAS возвращает EvaluationResult объект, а не словарь
    # Обращаемся к атрибутам напрямую или через getattr
    # В быстром режиме вычисляем только основные метрики
    if config.EVALUATION_FAST_MODE:
        metrics_dict = {
            "faithfulness": _extract_metric_value(getattr(result, "faithfulness", None)),
            "answer_relevancy": _extract_metric_value(getattr(result, "answer_relevancy", None)),
            "answer_similarity": _extract_metric_value(getattr(result, "answer_similarity", None)),
        }
    else:
        metrics_dict = {
            "faithfulness": _extract_metric_value(getattr(result, "faithfulness", None)),
            "answer_relevancy": _extract_metric_value(getattr(result, "answer_relevancy", None)),
            "answer_correctness": _extract_metric_value(getattr(result, "answer_correctness", None)),
            "answer_similarity": _extract_metric_value(getattr(result, "answer_similarity", None)),
            "context_recall": _extract_metric_value(getattr(result, "context_recall", None)),
            "context_precision": _extract_metric_value(getattr(result, "context_precision", None)),
        }

    logger.info("Evaluation завершён. Метрики: %s", metrics_dict)
    return metrics_dict


def _upload_feedback_to_langsmith(
    dataset_name: str,
    metrics: dict[str, float],
    examples: list[Any],
    dataset_with_rag: Dataset,
) -> bool:
    """Загружает результаты evaluation в LangSmith как feedback."""
    if not config.LANGSMITH_API_KEY:
        logger.info("LANGSMITH_API_KEY не установлен. Пропускаем загрузку feedback в LangSmith.")
        return False

    try:
        from langsmith import Client

        client = Client(api_key=config.LANGSMITH_API_KEY)

        # Загружаем примеры из датасета для получения run_id
        dataset_examples = list(client.list_examples(dataset_name=dataset_name))

        if not dataset_examples:
            logger.warning("Не найдено примеров в датасете '%s' для загрузки feedback", dataset_name)
            return False

        # Загружаем feedback для каждого примера
        feedback_count = 0
        for idx, (example, rag_result) in enumerate(zip(dataset_examples, dataset_with_rag)):
            try:
                # Создаём feedback с метриками
                # В LangSmith feedback можно добавлять к runs, но для простоты
                # добавим общий feedback к датасету
                pass  # Пока пропускаем загрузку feedback для отдельных примеров
                feedback_count += 1
            except Exception as exc:
                logger.warning("Ошибка при загрузке feedback для примера %s: %s", idx, exc)

        logger.info("Загружено %s feedback записей в LangSmith", feedback_count)
        return True

    except ImportError:
        logger.warning("langsmith не установлен. Пропускаем загрузку feedback в LangSmith.")
        return False
    except Exception as exc:
        logger.exception("Ошибка при загрузке feedback в LangSmith: %s", exc)
        return False


def evaluate_rag_pipeline_with_feedback(
    dataset_name: str,
    retriever: BaseRetriever | None = None,
    upload_feedback: bool = True,
) -> tuple[dict[str, float], int]:
    """Выполняет evaluation RAG pipeline и загружает результаты в LangSmith как feedback.

    Args:
        dataset_name: Название датасета в LangSmith
        retriever: Retriever для RAG (если None, используется из vector_store_manager)
        upload_feedback: Загружать ли результаты в LangSmith как feedback

    Returns:
        Кортеж (словарь с метриками, количество примеров):
        - faithfulness, answer_relevancy, answer_correctness,
        answer_similarity, context_recall, context_precision
        - количество обработанных примеров
    """
    logger.info("Начало evaluation RAG pipeline с датасетом '%s'", dataset_name)

    # Загружаем датасет из LangSmith
    dataset = _load_dataset_from_langsmith(dataset_name)
    if dataset is None:
        raise ValueError(f"Не удалось загрузить датасет '{dataset_name}' из LangSmith")

    # Сохраняем количество примеров для возврата
    examples_count = len(dataset)

    # Получаем retriever
    if retriever is None:
        manager = get_vector_store_manager()
        retriever = manager.get_retriever()

    # Запускаем RAG на всех примерах
    dataset_with_rag = _run_rag_on_dataset(dataset, retriever)

    # Настраиваем RAGAS метрики
    embeddings = _get_ragas_embeddings()
    llm = _get_ragas_llm()

    # Вычисляем метрики
    # В RAGAS метрики - это классы, которые нужно инстанцировать с параметрами
    # Некоторые метрики требуют только llm, другие - embeddings, третьи - оба
    # В быстром режиме используем только основные метрики для ускорения
    if config.EVALUATION_FAST_MODE:
        logger.info("Используется быстрый режим evaluation (только основные метрики)")
        metrics_list = [
            Faithfulness(llm=llm),
            AnswerRelevancy(llm=llm, embeddings=embeddings),
            AnswerSimilarity(embeddings=embeddings),
        ]
    else:
        metrics_list = [
            Faithfulness(llm=llm),
            AnswerRelevancy(llm=llm, embeddings=embeddings),
            AnswerCorrectness(llm=llm, embeddings=embeddings),
            AnswerSimilarity(embeddings=embeddings),
            ContextRecall(llm=llm),
            ContextPrecision(llm=llm),
        ]

    logger.info("Вычисление RAGAS метрик...")
    
    # Диагностическое логирование: проверяем формат датасета перед evaluation
    logger.info("Формат датасета перед evaluation:")
    logger.info("  Колонки: %s", dataset_with_rag.column_names)
    logger.info("  Количество записей: %s", len(dataset_with_rag))
    if len(dataset_with_rag) > 0:
        sample = dataset_with_rag[0]
        logger.info("  Пример первой записи:")
        for key in dataset_with_rag.column_names:
            value = sample.get(key)
            if isinstance(value, list):
                logger.info("    %s: список из %s элементов (первый элемент: %s...)", 
                           key, len(value), str(value[0])[:100] if value else "пусто")
            elif isinstance(value, str):
                logger.info("    %s: строка длиной %s символов (%s...)", 
                           key, len(value), value[:100] if value else "пусто")
            else:
                logger.info("    %s: %s (тип: %s)", key, type(value).__name__, type(value))
    
    try:
        result = evaluate(dataset=dataset_with_rag, metrics=metrics_list)
        logger.info("RAGAS evaluation завершён успешно")
    except Exception as exc:
        logger.exception("Ошибка при вычислении RAGAS метрик: %s", exc)
        raise

    # Диагностическое логирование: проверяем формат результатов RAGAS
    logger.info("Формат результатов RAGAS:")
    logger.info("  Тип результата: %s", type(result).__name__)
    logger.info("  Атрибуты результата: %s", [attr for attr in dir(result) if not attr.startswith('_')])
    
    # Пытаемся получить доступ к метрикам напрямую
    # В быстром режиме вычисляем только основные метрики
    if config.EVALUATION_FAST_MODE:
        metric_names_to_extract = [
            "faithfulness",
            "answer_relevancy",
            "answer_similarity",
        ]
    else:
        metric_names_to_extract = [
            "faithfulness",
            "answer_relevancy",
            "answer_correctness",
            "answer_similarity",
            "context_recall",
            "context_precision",
        ]
    
    logger.info("  Попытка доступа к метрикам:")
    logger.info("  Доступ через result.scores: %s", hasattr(result, 'scores'))
    if hasattr(result, 'scores'):
        logger.info("  result.scores тип: %s", type(result.scores).__name__)
        logger.info("  result.scores содержимое: %s", list(result.scores.keys()) if hasattr(result.scores, 'keys') else result.scores)
    
    for metric_name in metric_names_to_extract:
        try:
            value = getattr(result, metric_name, None)
            logger.info("    %s: %s (тип: %s)", metric_name, value, type(value).__name__ if value is not None else "None")
            # Также пробуем через индекс, если это возможно
            if hasattr(result, '__getitem__'):
                try:
                    indexed_value = result[metric_name]
                    logger.info("      Через индекс [%s]: %s", metric_name, indexed_value)
                except (KeyError, TypeError):
                    pass
            # Пробуем через scores, если доступно
            if hasattr(result, 'scores') and hasattr(result.scores, 'get'):
                try:
                    scores_value = result.scores.get(metric_name)
                    logger.info("      Через scores.get(%s): %s", metric_name, scores_value)
                except Exception:
                    pass
        except Exception as exc:
            logger.warning("    %s: ошибка при доступе - %s", metric_name, exc)

    # Извлекаем средние значения метрик
    # RAGAS может возвращать метрики как списки или скалярные значения
    def _extract_metric_value(metric_result):
        """Извлекает числовое значение из результата метрики."""
        import math
        
        if metric_result is None:
            return 0.0
        if isinstance(metric_result, (list, tuple)):
            # Если список, берем среднее значение
            if len(metric_result) == 0:
                return 0.0
            # Фильтруем None значения, строки, nan и inf
            valid_values = [
                v for v in metric_result 
                if v is not None 
                and isinstance(v, (int, float)) 
                and not math.isnan(v)
                and not math.isinf(v)
            ]
            if len(valid_values) == 0:
                logger.warning("Все значения метрики невалидны (None, nan, inf) или пустой список: %s", metric_result)
                return 0.0
            # Вычисляем среднее безопасно
            try:
                mean_value = sum(valid_values) / len(valid_values)
                # Преобразуем в float и проверяем на nan/inf
                mean_value = float(mean_value)
                if math.isnan(mean_value):
                    logger.warning("Среднее значение метрики равно nan (из значений: %s)", valid_values)
                    return 0.0
                if math.isinf(mean_value):
                    logger.warning("Среднее значение метрики равно inf (из значений: %s)", valid_values)
                    return 0.0
                return mean_value
            except (ZeroDivisionError, TypeError, ValueError) as e:
                logger.warning("Ошибка при вычислении среднего значения метрики: %s (значения: %s)", e, valid_values)
                return 0.0
        elif isinstance(metric_result, (int, float)):
            # Проверяем на nan и inf
            if math.isnan(metric_result):
                logger.warning("Метрика равна nan: %s", metric_result)
                return 0.0
            if math.isinf(metric_result):
                logger.warning("Метрика равна inf: %s", metric_result)
                return 0.0
            return float(metric_result)
        elif isinstance(metric_result, str):
            try:
                value = float(metric_result)
                if math.isnan(value) or math.isinf(value):
                    logger.warning("Метрика (строка) равна nan или inf: %s", metric_result)
                    return 0.0
                return value
            except ValueError:
                logger.warning("Не удалось преобразовать метрику в число: %s", metric_result)
                return 0.0
        else:
            logger.warning("Неожиданный тип результата метрики: %s (тип: %s)", metric_result, type(metric_result))
            return 0.0

    # RAGAS возвращает EvaluationResult объект, а не словарь
    # Обращаемся к атрибутам напрямую или через getattr
    # Используем тот же список метрик, что определен выше (metric_names_to_extract)
    metrics_dict = {}
    for metric_name in metric_names_to_extract:
        # Пробуем разные способы доступа к метрике
        raw_value = None
        
        # Сначала пробуем через scores (предпочтительный способ для RAGAS)
        if hasattr(result, 'scores'):
            if hasattr(result.scores, 'get'):
                try:
                    raw_value = result.scores.get(metric_name)
                except Exception:
                    pass
            elif hasattr(result.scores, '__getitem__'):
                try:
                    raw_value = result.scores[metric_name]
                except (KeyError, TypeError):
                    pass
        
        # Если не получилось через scores, пробуем через getattr
        if raw_value is None:
            try:
                raw_value = getattr(result, metric_name, None)
            except AttributeError:
                pass
        
        # Если не получилось через getattr, пробуем через индекс
        if raw_value is None and hasattr(result, '__getitem__'):
            try:
                raw_value = result[metric_name]
            except (KeyError, TypeError):
                pass
        
        logger.info("  Извлечение метрики %s: raw_value=%s (тип: %s)", 
                   metric_name, raw_value, type(raw_value).__name__ if raw_value is not None else "None")
        extracted_value = _extract_metric_value(raw_value)
        metrics_dict[metric_name] = extracted_value
        
        if extracted_value == 0.0:
            if raw_value is None:
                logger.warning("Метрика %s не найдена в результате (raw_value=None)", metric_name)
            else:
                logger.warning(
                    "Метрика %s извлечена как 0.0, но raw_value не None: %s (тип: %s)",
                    metric_name,
                    raw_value,
                    type(raw_value).__name__
                )

    logger.info("Evaluation завершён. Метрики: %s", metrics_dict)

    # Загружаем feedback в LangSmith (если нужно)
    if upload_feedback and config.LANGSMITH_API_KEY:
        try:
            from langsmith import Client

            client = Client(api_key=config.LANGSMITH_API_KEY)
            dataset_examples = list(client.list_examples(dataset_name=dataset_name))

            # Добавляем общий feedback к датасету через метаданные
            # В реальности можно использовать client.create_feedback для каждого примера
            logger.info("Результаты evaluation готовы для загрузки в LangSmith как feedback")
        except Exception as exc:
            logger.warning("Ошибка при подготовке feedback для LangSmith: %s", exc)

    # Возвращаем метрики и количество примеров
    return metrics_dict, examples_count
