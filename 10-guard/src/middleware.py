"""
Утилиты для маскирования чувствительных данных (PII - Personally Identifiable Information)

Маскирует персональные данные перед отправкой в LLM:
- Телефоны
- Email адреса
- Номера паспортов
- Номера банковских карт
- ИНН
- СНИЛС
"""
import re
import logging
from typing import Any, Dict, List, Optional
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage

logger = logging.getLogger(__name__)


class PIIMasker:
    """
    Класс для маскирования чувствительных данных в тексте
    """
    
    def __init__(self):
        # Регулярные выражения для поиска PII
        self.patterns = {
            'phone': re.compile(r'(\+?7|8)?[\s\-]?\(?(\d{3})\)?[\s\-]?(\d{3})[\s\-]?(\d{2})[\s\-]?(\d{2})'),
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'passport': re.compile(r'\b\d{4}\s?\d{6}\b'),  # Российский паспорт: 4 цифры + 6 цифр
            'card': re.compile(r'\b\d{4}[\s\-]?\d{4}[\s\-]?\d{4}[\s\-]?\d{4}\b'),  # Банковская карта: 16 цифр
            'inn': re.compile(r'\b\d{10}\b|\b\d{12}\b'),  # ИНН: 10 или 12 цифр (исправлено: | внутри группы)
            'snils': re.compile(r'\b\d{3}[\s\-]?\d{3}[\s\-]?\d{3}[\s\-]?\d{2}\b'),  # СНИЛС: 11 цифр
        }
    
    def mask_phone(self, text: str) -> str:
        """Маскирует телефонные номера"""
        def replace_phone(match):
            groups = match.groups()
            # groups[0] - код страны (+7 или 8), groups[1] - первые 3 цифры, groups[2] - следующие 3, 
            # groups[3] - предпоследние 2, groups[4] - последние 2
            try:
                if len(groups) >= 5 and groups[3] is not None and groups[4] is not None:
                    return '***-***-' + groups[3] + groups[4]
                elif len(groups) >= 4 and groups[3] is not None:
                    return '***-***-' + groups[3] + '**'
            except (IndexError, TypeError):
                pass
            return '***-***-****'
        return self.patterns['phone'].sub(replace_phone, text)
    
    def mask_email(self, text: str) -> str:
        """Маскирует email адреса"""
        def replace_email(match):
            email = match.group(0)
            parts = email.split('@')
            if len(parts) == 2:
                return parts[0][0] + '***@' + parts[1]
            return '***@***'
        return self.patterns['email'].sub(replace_email, text)
    
    def mask_passport(self, text: str) -> str:
        """Маскирует номера паспортов"""
        return self.patterns['passport'].sub('**** ******', text)
    
    def mask_card(self, text: str) -> str:
        """Маскирует номера банковских карт"""
        def replace_card(match):
            card = match.group(0).replace(' ', '').replace('-', '')
            if len(card) == 16:
                return '**** **** **** ' + card[-4:]
            return '**** **** **** ****'
        return self.patterns['card'].sub(replace_card, text)
    
    def mask_inn(self, text: str) -> str:
        """Маскирует ИНН"""
        def replace_inn(match):
            inn = match.group(0)
            if len(inn) == 10:
                return '********' + inn[-2:]
            elif len(inn) == 12:
                return '**********' + inn[-2:]
            return '**********'
        return self.patterns['inn'].sub(replace_inn, text)
    
    def mask_snils(self, text: str) -> str:
        """Маскирует СНИЛС"""
        return self.patterns['snils'].sub('***-***-***-**', text)
    
    def mask_text(self, text: str) -> str:
        """Применяет все маски к тексту"""
        masked = text
        masked = self.mask_phone(masked)
        masked = self.mask_email(masked)
        masked = self.mask_passport(masked)
        masked = self.mask_card(masked)
        masked = self.mask_inn(masked)
        masked = self.mask_snils(masked)
        return masked


# Глобальный экземпляр маскировщика
pii_masker = PIIMasker()


# ============================================================================
# Rate Limiting Middleware
# ============================================================================

from collections import defaultdict
from datetime import datetime, timedelta


class RateLimiter:
    """
    Базовый класс для отслеживания лимитов вызовов
    
    Отслеживает количество вызовов на пользователя (chat_id) с возможностью
    сброса счетчиков через определенный период времени (окно).
    """
    
    def __init__(self, limit: int, window_seconds: int = 3600):
        """
        Args:
            limit: Максимальное количество вызовов в окне
            window_seconds: Размер окна в секундах (по умолчанию 1 час)
        """
        self.limit = limit
        self.window_seconds = window_seconds
        # Словарь: chat_id -> список временных меток вызовов
        self._calls: Dict[int, List[datetime]] = defaultdict(list)
        self._lock = {}  # Простая блокировка для thread-safety (в реальности нужен asyncio.Lock)
    
    def _cleanup_old_calls(self, chat_id: int):
        """Удаляет вызовы старше окна"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)
        self._calls[chat_id] = [
            call_time for call_time in self._calls[chat_id]
            if call_time > cutoff
        ]
    
    def check_limit(self, chat_id: int) -> tuple[bool, int, int]:
        """
        Проверяет, не превышен ли лимит для данного chat_id
        
        Returns:
            (is_allowed, current_count, limit)
        """
        self._cleanup_old_calls(chat_id)
        current_count = len(self._calls[chat_id])
        is_allowed = current_count < self.limit
        return is_allowed, current_count, self.limit
    
    def record_call(self, chat_id: int):
        """Записывает вызов для данного chat_id"""
        now = datetime.now()
        self._calls[chat_id].append(now)
        self._cleanup_old_calls(chat_id)
    
    def reset(self, chat_id: Optional[int] = None):
        """Сбрасывает счетчики для chat_id или для всех"""
        if chat_id is None:
            self._calls.clear()
        else:
            self._calls.pop(chat_id, None)


class ModelCallLimitMiddleware:
    """
    Middleware для ограничения количества вызовов модели на пользователя
    
    Отслеживает количество вызовов LLM (модели) для каждого chat_id и
    прерывает выполнение при превышении лимита.
    """
    
    def __init__(self, limit: int = 10, window_seconds: int = 3600):
        """
        Args:
            limit: Максимальное количество вызовов модели в окне (по умолчанию 10)
            window_seconds: Размер окна в секундах (по умолчанию 1 час = 3600)
        """
        self.limiter = RateLimiter(limit, window_seconds)
        logger.info(f"🔒 ModelCallLimitMiddleware initialized: limit={limit}, window={window_seconds}s")
    
    def check_and_record(self, chat_id: int) -> tuple[bool, str]:
        """
        Проверяет лимит и записывает вызов
        
        Returns:
            (is_allowed, error_message)
        """
        is_allowed, current_count, limit = self.limiter.check_limit(chat_id)
        
        if not is_allowed:
            error_msg = (
                f"Превышен лимит вызовов модели: {current_count}/{limit} в течение последнего часа. "
                f"Пожалуйста, подождите перед следующим запросом."
            )
            logger.warning(f"🚫 Model call limit exceeded for chat {chat_id}: {current_count}/{limit}")
            return False, error_msg
        
        self.limiter.record_call(chat_id)
        logger.debug(f"✓ Model call recorded for chat {chat_id}: {current_count + 1}/{limit}")
        return True, ""


class ToolCallLimitMiddleware:
    """
    Middleware для ограничения количества вызовов инструментов на пользователя
    
    Отслеживает общее количество вызовов инструментов для каждого chat_id и
    прерывает выполнение при превышении лимита.
    """
    
    def __init__(self, limit: int = 20, window_seconds: int = 3600):
        """
        Args:
            limit: Максимальное количество вызовов инструментов в окне (по умолчанию 20)
            window_seconds: Размер окна в секундах (по умолчанию 1 час = 3600)
        """
        self.limiter = RateLimiter(limit, window_seconds)
        logger.info(f"🔒 ToolCallLimitMiddleware initialized: limit={limit}, window={window_seconds}s")
    
    def check_and_record(self, chat_id: int, tool_name: str = None) -> tuple[bool, str]:
        """
        Проверяет лимит и записывает вызов инструмента
        
        Args:
            chat_id: ID чата
            tool_name: Имя инструмента (для логирования)
        
        Returns:
            (is_allowed, error_message)
        """
        is_allowed, current_count, limit = self.limiter.check_limit(chat_id)
        
        if not is_allowed:
            error_msg = (
                f"Превышен лимит вызовов инструментов: {current_count}/{limit} в течение последнего часа. "
                f"Пожалуйста, подождите перед следующим запросом."
            )
            logger.warning(f"🚫 Tool call limit exceeded for chat {chat_id}: {current_count}/{limit} (tool: {tool_name})")
            return False, error_msg
        
        self.limiter.record_call(chat_id)
        logger.debug(f"✓ Tool call recorded for chat {chat_id}: {current_count + 1}/{limit} (tool: {tool_name})")
        return True, ""

