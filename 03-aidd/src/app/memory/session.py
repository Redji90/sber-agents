# src/app/memory/session.py
import logging
from collections import defaultdict, deque
from typing import Deque, Dict, List

from src.app import config

logger = logging.getLogger(__name__)

# Словарь для хранения сессий: {user_id: deque_сообщений}
# Используем defaultdict для автоматического создания deque для нового user_id
sessions: Dict[int, Deque[Dict[str, str]]] = defaultdict(lambda: deque(maxlen=config.CONTEXT_TURNS))

class SessionManager:
    def add_message(self, user_id: int, role: str, content: str) -> None:
        """Добавляет сообщение в историю сессии пользователя, обрезая старые сообщения."""
        sessions[user_id].append({"role": role, "content": content})
        logger.debug(f"Сообщение [{role}] для пользователя {user_id} добавлено. Текущая длина: {len(sessions[user_id])}")

    def get_messages(self, user_id: int) -> List[Dict[str, str]]:
        """Возвращает текущую историю сообщений для пользователя."""
        return list(sessions[user_id])

    def clear_session(self, user_id: int) -> None:
        """Очищает историю сообщений для пользователя."""
        if user_id in sessions:
            del sessions[user_id]
            logger.info(f"Сессия для пользователя {user_id} очищена.")
        else:
            logger.debug(f"Попытка очистить несуществующую сессию для пользователя {user_id}.")
