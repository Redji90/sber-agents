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
from src.app.indexing import describe_index_status, run_full_indexing
from src.app.indexing.vector_store import get_vector_store_manager
from src.app.memory.session import SessionManager
from src.app.rag.chain import build_rag_chain

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
    await message.answer(
        "Я банковский ассистент. Задавайте вопросы, и я отвечу на них."
    )


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


def _format_sources(documents: List[Document]) -> str:
    if not documents:
        return "Источники: не найдено."

    lines = ["Источники:"]
    for idx, doc in enumerate(documents, start=1):
        source = doc.metadata.get("source") or "неизвестно"
        page = doc.metadata.get("page")
        page_info = f", страница {page}" if page is not None else ""
        lines.append(f"{idx}. {source}{page_info}")
    return "\n".join(lines)


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

        response_text = f"{answer}\n\n{_format_sources(documents)}"
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
