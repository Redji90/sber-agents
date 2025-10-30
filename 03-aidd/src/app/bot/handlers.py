# src/app/bot/handlers.py
import logging
from aiogram import Router, types
from aiogram.filters import Command
from openai.types.chat import ChatCompletionMessageParam

from src.app.llm.client import LLMClient
from src.app.memory.session import SessionManager
from src.app import config

logger = logging.getLogger(__name__)
router = Router()

llm_client = LLMClient()
session_manager = SessionManager()

@router.message(Command("start"))
async def command_start_handler(message: types.Message) -> None:
    """Обрабатывает команду /start."""
    user_id = message.from_user.id if message.from_user else -1
    logger.info(f"Получена команда /start от пользователя: {user_id}")

    # Очистка сессии при старте
    session_manager.clear_session(user_id)

    await message.answer(
        "Привет! Я банковский ассистент. Задавайте вопросы, и я помогу вам."
    )

@router.message(Command("help"))
async def command_help_handler(message: types.Message) -> None:
    """Обрабатывает команду /help."""
    user_id = message.from_user.id if message.from_user else "unknown"
    logger.info(f"Получена команда /help от пользователя: {user_id}")
    await message.answer(
        "Я банковский ассистент. Задавайте вопросы, и я отвечу на них."
    )

@router.message(Command("reset")) # Новый обработчик для команды /reset
async def command_reset_handler(message: types.Message) -> None:
    """Обрабатывает команду /reset."""
    user_id = message.from_user.id if message.from_user else -1
    logger.info(f"Получена команда /reset от пользователя: {user_id}. Очистка сессии.")
    session_manager.clear_session(user_id)
    await message.answer("История диалога очищена. Начинаем с чистого листа.")

@router.message()
async def handle_text_message(message: types.Message) -> None:
    """Обрабатывает текстовые сообщения пользователя."""
    user_id = message.from_user.id if message.from_user else -1
    if not message.text:
        logger.info(f"Получено нетекстовое сообщение от {user_id}. Игнорируем.")
        return

    logger.info(f"Получено текстовое сообщение от {user_id}. Длина: {len(message.text)}")

    # Добавляем сообщение пользователя в сессию
    session_manager.add_message(user_id, "user", message.text)

    await message.bot.send_chat_action(chat_id=message.chat.id, action="typing")

    # Получаем всю историю сообщений для LLM
    messages_for_llm: list[ChatCompletionMessageParam] = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in session_manager.get_messages(user_id)
    ]

    try:
        response_text = await llm_client.generate(messages_for_llm)
        logger.info(f"Ответ LLM для {user_id}. Длина: {len(response_text)}")
        await message.answer(response_text)

        # Добавляем ответ бота в сессию
        session_manager.add_message(user_id, "assistant", response_text)

    except Exception:
        logger.error(f"Ошибка при получении ответа от LLM для пользователя {user_id}")
        await message.answer("Извините, произошла ошибка при обработке вашего запроса. Попробуйте позже.")
