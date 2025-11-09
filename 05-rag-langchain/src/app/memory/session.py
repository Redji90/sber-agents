# src/app/memory/session.py
import logging
from collections import defaultdict, deque
from typing import Deque, Dict, List

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from src.app import config

logger = logging.getLogger(__name__)

# Словарь для хранения сессий: {user_id: deque сообщений}
sessions: Dict[int, Deque[BaseMessage]] = defaultdict(lambda: deque(maxlen=config.CONTEXT_TURNS))


class SessionManager:
    def add_message(self, user_id: int, message: BaseMessage) -> None:
        """Добавляет сообщение в историю сессии пользователя."""
        sessions[user_id].append(message)
        logger.debug(
            "Добавлено сообщение типа %s для пользователя %s. Текущая длина: %s",
            type(message).__name__,
            user_id,
            len(sessions[user_id]),
        )

    def add_user_message(self, user_id: int, content: str) -> None:
        self.add_message(user_id, HumanMessage(content=content))

    def add_ai_message(self, user_id: int, content: str) -> None:
        self.add_message(user_id, AIMessage(content=content))

    def get_messages(self, user_id: int) -> List[BaseMessage]:
        """Возвращает текущую историю сообщений пользователя."""
        return list(sessions[user_id])

    def clear_session(self, user_id: int) -> None:
        """Очищает историю сообщений пользователя."""
        if user_id in sessions:
            del sessions[user_id]
            logger.info("Сессия для пользователя %s очищена.", user_id)
        else:
            logger.debug("Попытка очистить несуществующую сессию пользователя %s.", user_id)
