# src/app/llm/client.py
import logging
from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam

from src.app import config

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(self):
        # Для OpenRouter и других провайдеров используем умеренные настройки retry
        # Большое количество retry при 429 ошибках только усугубляет ситуацию
        self.client = AsyncOpenAI(
            base_url=config.OPENAI_BASE_URL,
            api_key=config.OPENAI_API_KEY,
            timeout=60.0,  # Разумный таймаут
            max_retries=3,  # Умеренное количество retry (OpenAI клиент сам делает exponential backoff)
        )
        logger.info(f"LLMClient инициализирован с base_url: {config.OPENAI_BASE_URL}")

    async def generate(self, messages: list[ChatCompletionMessageParam]) -> str:
        """
        Отправляет запрос к LLM и возвращает сгенерированный текст.
        :param messages: Список сообщений в формате OpenAI Chat API.
        :return: Текст ответа от LLM.
        """
        try:
            full_messages = [
                {"role": "system", "content": config.SYSTEM_ROLE},
                *messages,
            ]
            
            logger.debug(f"Отправка запроса к LLM. Модель: {config.LLM_MODEL}, сообщений: {len(full_messages)}")
            
            response = await self.client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=full_messages,
                temperature=1.0, # По умолчанию
                max_tokens=1000, # По умолчанию
            )
            
            content = response.choices[0].message.content
            logger.debug(f"Получен ответ от LLM. Длина: {len(content)}, Содержимое: '{content}'")

            if not content or content.strip() == "":
                logger.warning("LLM вернула пустой или бессодержательный ответ.")
                return "Извините, LLM не смогла дать осмысленный ответ."

            return content

        except Exception as e:
            logger.exception(f"Ошибка при обращении к LLM: {e}")
            raise  # Передаем ошибку выше для обработки в хендлере
