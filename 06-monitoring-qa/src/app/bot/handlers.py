# src/app/bot/handlers.py
import asyncio
import logging
from typing import List

from aiogram import Router, types
from aiogram.filters import Command
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from openai import BadRequestError

from indexer_with_json import reindex_all
from src.app import config
from src.app.evaluation.evaluation import (
    evaluate_rag_pipeline_with_feedback,
    _load_dataset_from_langsmith,
    _run_rag_on_dataset,
)
from src.app.indexing import describe_index_status, run_full_indexing
from src.app.indexing.vector_store import get_vector_store_manager
from src.app.memory.session import SessionManager
from src.app.rag.chain import build_rag_chain
from src.app.synthesis.dataset_synthesizer import synthesize_dataset

logger = logging.getLogger(__name__)
router = Router()

session_manager = SessionManager()


@router.message(Command("start"))
async def command_start_handler(message: types.Message) -> None:
    """Обрабатывает команду /start."""
    user_id = message.from_user.id if message.from_user else -1
    logger.info("Получена команда /start от пользователя: %s", user_id)

    session_manager.clear_session(user_id)

    await message.answer(
        "Привет! Я банковский ассистент. Задавайте вопросы, и я помогу вам."
    )


@router.message(Command("help"))
async def command_help_handler(message: types.Message) -> None:
    """Обрабатывает команду /help."""
    user_id = message.from_user.id if message.from_user else "unknown"
    logger.info("Получена команда /help от пользователя: %s", user_id)
    help_text = (
        "Я банковский ассистент. Задавайте вопросы, и я отвечу на них.\n\n"
        "Доступные команды:\n"
        "/start - Начать диалог\n"
        "/help - Показать эту справку\n"
        "/reset - Очистить историю диалога\n"
        "/index - Переиндексировать документы\n"
        "/index_status - Проверить статус индексации\n"
    )
    if config.LANGSMITH_API_KEY:
        help_text += "/synthesize_dataset - Создать тестовый датасет из документов\n"
        help_text += "/evaluate_dataset - Запустить evaluation качества RAG pipeline\n"
    await message.answer(help_text)


@router.message(Command("reset"))
async def command_reset_handler(message: types.Message) -> None:
    """Обрабатывает команду /reset."""
    user_id = message.from_user.id if message.from_user else -1
    logger.info("Получена команда /reset от пользователя %s. Очистка сессии.", user_id)
    session_manager.clear_session(user_id)
    await message.answer("История диалога очищена. Начинаем с чистого листа.")


@router.message(Command("index"))
async def command_index_handler(message: types.Message) -> None:
    """Запускает переиндексацию данных."""
    user_id = message.from_user.id if message.from_user else -1
    manager = get_vector_store_manager()
    status = manager.status.state

    if status == "running":
        logger.info("Пользователь %s запросил /index, но индексация уже идёт.", user_id)
        await message.answer("Индексация уже выполняется. Проверьте статус позже командой /index_status.")
        return

    logger.info("Запуск переиндексации по запросу пользователя %s.", user_id)
    await message.answer("Запускаю переиндексацию данных. Проверьте статус через /index_status.")
    asyncio.create_task(run_full_indexing())


@router.message(Command("index_status"))
async def command_index_status_handler(message: types.Message) -> None:
    """Возвращает статус текущего индекса."""
    user_id = message.from_user.id if message.from_user else -1
    logger.info("Пользователь %s запросил /index_status.", user_id)
    status_message = describe_index_status()
    await message.answer(status_message)


@router.message(Command("synthesize_dataset"))
async def command_synthesize_dataset_handler(message: types.Message) -> None:
    """Создаёт тестовый датасет из документов для evaluation."""
    user_id = message.from_user.id if message.from_user else -1
    logger.info("Получена команда /synthesize_dataset от пользователя %s.", user_id)

    # Проверяем наличие LangSmith API ключа
    if not config.LANGSMITH_API_KEY:
        await message.answer(
            "❌ LangSmith API ключ не установлен. "
            "Установите переменную окружения LANGSMITH_API_KEY для синтеза датасета."
        )
        return

    # Название датасета по умолчанию
    dataset_name = config.LANGSMITH_PROJECT or "06-rag-qa-dataset"

    await message.answer(
        f"🔄 Начинаю синтез датасета '{dataset_name}' из документов. "
        "Это может занять некоторое время..."
    )

    try:
        # Запускаем синтез в фоновом режиме
        def run_synthesis():
            return synthesize_dataset(
                dataset_name=dataset_name,
                upload_to_langsmith=True,
            )

        saved_path = await asyncio.to_thread(run_synthesis)

        await message.answer(
            f"✅ Датасет '{dataset_name}' успешно создан и загружен в LangSmith!\n\n"
            f"Путь к файлу: {saved_path}\n\n"
            "Теперь вы можете запустить evaluation командой /evaluate_dataset"
        )
        logger.info("Синтез датасета завершён для пользователя %s. Файл: %s", user_id, saved_path)

    except Exception as exc:
        logger.exception("Ошибка при синтезе датасета для пользователя %s: %s", user_id, exc)
        await message.answer(
            f"❌ Произошла ошибка при создании датасета: {exc}\n"
            "Проверьте логи для получения подробной информации."
        )


@router.message(Command("debug_eval_examples"))
async def command_debug_eval_examples_handler(message: types.Message) -> None:
    """Показывает несколько примеров из evaluation: вопрос, эталон, ответ RAG и первый контекст.

    Важно: использует тот же in-memory индекс и retriever, что и основной бот,
    поэтому команду имеет смысл вызывать после /index.
    """
    user_id = message.from_user.id if message.from_user else -1
    logger.info("Получена команда /debug_eval_examples от пользователя %s.", user_id)

    if not config.LANGSMITH_API_KEY:
        await message.answer(
            "❌ LangSmith API ключ не установлен. "
            "Установите переменную окружения LANGSMITH_API_KEY, чтобы загружать датасет."
        )
        return

    manager = get_vector_store_manager()
    status = manager.status
    if status.chunks == 0:
        await message.answer(
            "❌ Индекс пуст. Для отладки evaluation нужен индекс документов.\n\n"
            "Сначала запустите /index и дождитесь завершения, затем повторите команду."
        )
        return

    dataset_name = config.LANGSMITH_PROJECT or "06-monitoring-qa"
    await message.answer(
        f"🔍 Загружаю датасет '{dataset_name}' и прогоняю первые примеры через RAG..."
    )

    try:
        # Загружаем датасет и берём несколько первых примеров
        dataset = _load_dataset_from_langsmith(dataset_name)
        if dataset is None or len(dataset) == 0:
            await message.answer(
                f"❌ Не удалось загрузить датасет '{dataset_name}' из LangSmith "
                "или он пуст."
            )
            return

        examples_to_show = min(3, len(dataset))
        subset = dataset.select(range(examples_to_show))

        retriever = manager.get_retriever()

        # _run_rag_on_dataset внутри использует asyncio.run, поэтому запускаем его в отдельном потоке
        dataset_with_rag = await asyncio.to_thread(
            _run_rag_on_dataset,
            subset,
            retriever,
        )

        lines: list[str] = []
        for idx in range(examples_to_show):
            ex = dataset_with_rag[idx]
            question = ex.get("question", "")
            ground_truths = ex.get("ground_truths") or [""]
            ground_truth = ground_truths[0] if ground_truths else ""
            answer = ex.get("answer", "")
            contexts = ex.get("contexts") or []
            first_context = contexts[0] if contexts else ""

            def _short(text: str, limit: int = 300) -> str:
                text = (text or "").replace("\n", " ")
                return text[:limit] + ("..." if len(text) > limit else "")

            lines.append(
                f"=== Пример {idx + 1} ===\n"
                f"❓ Вопрос: {_short(question)}\n"
                f"✅ Эталон: {_short(ground_truth)}\n"
                f"🤖 Ответ RAG: {_short(answer)}\n"
                f"📚 Первый контекст: {_short(first_context) if first_context else '<нет контекста>'}\n"
            )

        text = "Вот несколько примеров из датасета и ответы текущего RAG:\n\n" + "\n".join(lines)
        await message.answer(text)
        logger.info(
            "Отправлены debug-примеры evaluation пользователю %s (dataset=%s, examples=%s).",
            user_id,
            dataset_name,
            examples_to_show,
        )
    except Exception as exc:
        logger.exception("Ошибка в /debug_eval_examples для пользователя %s: %s", user_id, exc)
        await message.answer(
            "❌ Произошла ошибка при отладке evaluation. "
            "Проверьте логи для подробностей."
        )


@router.message(Command("evaluate_dataset"))
async def command_evaluate_dataset_handler(message: types.Message) -> None:
    """Запускает evaluation RAG pipeline через RAGAS метрики."""
    user_id = message.from_user.id if message.from_user else -1
    logger.info("Получена команда /evaluate_dataset от пользователя %s.", user_id)

    # Проверяем наличие LangSmith API ключа
    if not config.LANGSMITH_API_KEY:
        await message.answer(
            "❌ LangSmith API ключ не установлен. "
            "Установите переменную окружения LANGSMITH_API_KEY для использования evaluation."
        )
        return

    # Проверяем наличие индекса
    # Индекс нужен для RAG pipeline: evaluation запускает RAG на каждом вопросе из датасета,
    # и RAG использует retriever для поиска релевантных документов в индексе
    manager = get_vector_store_manager()
    status = manager.status

    if status.chunks == 0:
        await message.answer(
            "❌ Индекс пуст. Для evaluation нужен индекс документов.\n\n"
            "Evaluation запускает RAG pipeline на каждом вопросе из датасета:\n"
            "1. Вопрос из датасета\n"
            "2. RAG ищет релевантные документы в индексе\n"
            "3. RAG генерирует ответ на основе найденных документов\n"
            "4. RAGAS вычисляет метрики качества ответов\n\n"
            "Запустите /index и дождитесь завершения, затем повторите команду."
        )
        return

    # Название датасета по умолчанию
    dataset_name = config.LANGSMITH_PROJECT or "06-rag-qa-dataset"

    await message.answer(
        f"🔄 Запускаю evaluation датасета '{dataset_name}'. Это может занять некоторое время..."
    )

    try:
        # Запускаем evaluation в фоновом режиме
        retriever = manager.get_retriever()
        result = await asyncio.to_thread(
            evaluate_rag_pipeline_with_feedback,
            dataset_name=dataset_name,
            retriever=retriever,
            upload_feedback=True,
        )
        
        # Результат может быть словарем метрик или кортежем (метрики, количество примеров)
        if isinstance(result, tuple):
            metrics, examples_count = result
        else:
            metrics = result
            # Получаем количество примеров из датасета
            try:
                from langsmith import Client
                client = Client(api_key=config.LANGSMITH_API_KEY)
                dataset_info = client.read_dataset(dataset_name=dataset_name)
                examples_count = dataset_info.example_count if hasattr(dataset_info, 'example_count') else len(metrics.get('faithfulness', [])) if isinstance(metrics.get('faithfulness'), list) else '?'
            except Exception:
                examples_count = len(metrics.get('faithfulness', [])) if isinstance(metrics.get('faithfulness'), list) else '?'

        # Словарь соответствия английских названий метрик русским названиям и цветам
        metric_translations = {
            "faithfulness": ("Обоснованность (нет галлюцинаций)", "🟢"),
            "answer_relevancy": ("Релевантность ответа", "🟡"),
            "answer_correctness": ("Правильность ответа", "🟢"),
            "answer_similarity": ("Похожесть на эталон", "🟢"),
            "context_recall": ("Полнота контекста", "🟡"),
            "context_precision": ("Точность поиска", "🟢"),
        }
        
        # Определяем цвет кружка на основе значения метрики
        def get_metric_emoji(metric_name: str, value: float) -> str:
            """Возвращает эмодзи кружка в зависимости от значения метрики."""
            # Для метрик качества: зеленый > 0.7, желтый 0.5-0.7, красный < 0.5
            if value >= 0.7:
                return "🟢"
            elif value >= 0.5:
                return "🟡"
            else:
                return "🔴"
        
        # Форматируем результаты на русском языке
        metrics_text = "✅ Evaluation завершен!\n\n"
        metrics_text += f"📊 Датасет: {dataset_name}\n"
        metrics_text += f"📝 Примеров обработано: {examples_count}\n\n"
        metrics_text += "🎯 RAGAS Метрики:\n"
        
        for metric_name, metric_value in metrics.items():
            # Получаем русское название и цвет
            if metric_name in metric_translations:
                russian_name, _ = metric_translations[metric_name]
                emoji = get_metric_emoji(metric_name, metric_value)
            else:
                # Если метрика не в словаре, используем английское название
                russian_name = metric_name.replace("_", " ").title()
                emoji = get_metric_emoji(metric_name, metric_value)
            
            # Округляем до 3 знаков после запятой
            metric_value_str = f"{metric_value:.3f}"
            metrics_text += f"{emoji} {russian_name}: {metric_value_str}\n"

        metrics_text += "\n💡 Результаты загружены в LangSmith как feedback"

        await message.answer(metrics_text)
        logger.info("Evaluation завершён для пользователя %s. Метрики: %s", user_id, metrics)

    except ValueError as exc:
        error_msg = str(exc)
        logger.warning("Ошибка при evaluation для пользователя %s: %s", user_id, error_msg)
        await message.answer(f"❌ Ошибка: {error_msg}")
    except Exception as exc:
        logger.exception("Ошибка при evaluation для пользователя %s: %s", user_id, exc)
        await message.answer(
            "❌ Произошла ошибка при выполнении evaluation. "
            "Проверьте логи для получения подробной информации."
        )


def _format_sources(documents: List[Document]) -> str:
    """Форматирует источники в формате: '📚 Источники: filename.pdf (стр. 1, 3, 5)'."""
    if not documents:
        return "📚 Источники: не найдено."

    # Группируем документы по источнику и собираем уникальные страницы
    source_pages: dict[str, set[int]] = {}
    for doc in documents:
        source = doc.metadata.get("source") or "неизвестно"
        # Извлекаем только имя файла из полного пути
        filename = source.split("/")[-1] if "/" in source else source
        filename = filename.split("\\")[-1] if "\\" in filename else filename

        page = doc.metadata.get("page")
        if page is not None:
            if filename not in source_pages:
                source_pages[filename] = set()
            source_pages[filename].add(page)

    if not source_pages:
        return "📚 Источники: не найдено."

    # Форматируем список источников
    sources_list = []
    for filename, pages in sorted(source_pages.items()):
        pages_str = ", ".join(map(str, sorted(pages)))
        sources_list.append(f"{filename} (стр. {pages_str})")

    return f"📚 Источники: {', '.join(sources_list)}"


@router.message()
async def handle_text_message(message: types.Message) -> None:
    """Обрабатывает текстовые сообщения пользователя."""
    user_id = message.from_user.id if message.from_user else -1
    if not message.text:
        logger.info("Получено нетекстовое сообщение от %s. Игнорируем.", user_id)
        return

    logger.info("Получено текстовое сообщение от %s. Длина: %s", user_id, len(message.text))
    manager = get_vector_store_manager()
    status = manager.status

    if status.chunks == 0:
        logger.info("Ответ невозможен: индекс пуст или не готов.")
        await message.answer(
            "Индекс пока пуст. Запустите /index и дождитесь завершения, затем повторите вопрос."
        )
        return

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    chat_history: List[BaseMessage] = session_manager.get_messages(user_id)
    retriever = manager.get_retriever()
    rag_chain = build_rag_chain(retriever)

    try:
        result = await rag_chain.ainvoke({"input": message.text, "chat_history": chat_history})
        answer: str = result.get("answer", "").strip()
        documents: List[Document] = result.get("context", [])

        if not answer:
            answer = "Извините, я не смог найти ответ в документе."

        # Добавляем источники только если SHOW_SOURCES=true
        response_text = answer
        if config.SHOW_SOURCES:
            sources = _format_sources(documents)
            response_text = f"{answer}\n\n{sources}"

        session_manager.add_user_message(user_id, message.text)
        session_manager.add_ai_message(user_id, answer)

        logger.info("Ответ пользователю %s подготовлен. Чанков в ответе: %s", user_id, len(documents))
        await message.answer(response_text)

    except BadRequestError as exc:
        logger.warning(
            "Некорректный запрос к LLM для пользователя %s: %s", user_id, exc
        )
        await message.answer(
            "Не получилось обработать запрос. Попробуйте переформулировать вопрос или уточнить детали."
        )
    except Exception as exc:
        logger.exception("Ошибка при обработке RAG-запроса для пользователя %s: %s", user_id, exc)
        await message.answer("Извините, произошла ошибка при обработке вашего запроса. Попробуйте позже.")
