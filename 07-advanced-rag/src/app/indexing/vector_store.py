"""Управление in-memory векторным хранилищем и статусом индексации."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Literal, Sequence
from datetime import datetime, timezone

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_community.vectorstores import InMemoryVectorStore

from src.app import config

logger = logging.getLogger(__name__)


@dataclass
class IndexStatus:
    state: Literal["idle", "running", "ready", "error"] = "idle"
    chunks: int = 0
    updated_at: datetime | None = None
    error_message: str | None = None


class VectorStoreManager:
    """Хранит ссылку на векторное хранилище и текущий статус индексации."""

    def __init__(self, embeddings: Embeddings):
        self._embeddings = embeddings
        self._vector_store = InMemoryVectorStore(embedding=embeddings)
        self._status = IndexStatus()
        self._documents: list[Document] = []  # Храним документы для BM25 индексации

    @property
    def status(self) -> IndexStatus:
        return self._status

    @property
    def embeddings(self) -> Embeddings:
        return self._embeddings

    @property
    def vector_store(self) -> InMemoryVectorStore:
        return self._vector_store

    def start_indexing(self) -> None:
        self._status = IndexStatus(
            state="running",
            chunks=0,
            updated_at=datetime.now(timezone.utc),
            error_message=None,
        )

    def finish_indexing(self, chunks: int) -> None:
        self._status = IndexStatus(
            state="ready",
            chunks=chunks,
            updated_at=datetime.now(timezone.utc),
            error_message=None,
        )

    def fail_indexing(self, message: str | None = None) -> None:
        self._status = IndexStatus(
            state="error",
            chunks=self._status.chunks,
            updated_at=datetime.now(timezone.utc),
            error_message=message,
        )

    def reset(self) -> None:
        self._vector_store = InMemoryVectorStore(embedding=self._embeddings)
        self._status = IndexStatus(
            state="idle",
            chunks=0,
            updated_at=datetime.now(timezone.utc),
            error_message=None,
        )

    def replace_store(self, vector_store: InMemoryVectorStore, chunks: int, documents: Sequence[Document] | None = None) -> None:
        """Заменяет векторное хранилище и обновляет статус.

        Args:
            vector_store: Новое векторное хранилище
            chunks: Количество чанков
            documents: Список документов для сохранения (нужен для BM25 индексации)
        """
        self._vector_store = vector_store
        if documents is not None:
            self._documents = list(documents)
        self.finish_indexing(chunks)

    def get_documents(self) -> list[Document]:
        """Возвращает список документов для BM25 индексации.

        Returns:
            Список документов
        """
        return self._documents.copy()

    def set_status(self, state: Literal["idle", "running", "ready", "error"], chunks: int | None = None) -> None:
        self._status = IndexStatus(
            state=state,
            chunks=chunks if chunks is not None else self._status.chunks,
            updated_at=datetime.now(timezone.utc),
            error_message=self._status.error_message,
        )

    def get_retriever(self, k: int | None = None) -> BaseRetriever:
        """Возвращает semantic retriever с указанным k.

        Args:
            k: Количество документов для возврата (по умолчанию SEMANTIC_K для Advanced RAG)

        Returns:
            Semantic retriever из InMemoryVectorStore
        """
        if k is None:
            k = config.SEMANTIC_K if config.RAG_MODE != "semantic" else config.RETRIEVER_K
        return self._vector_store.as_retriever(search_kwargs={"k": k})

    def build_store_from_documents(self, documents: Sequence[Document]) -> InMemoryVectorStore:
        """Создаёт векторное хранилище из документов с обработкой ошибок и rate limiting."""
        import logging
        import time
        
        logger = logging.getLogger(__name__)
        
        # Определяем, какой провайдер используется
        provider = config.EMBEDDINGS_PROVIDER.lower()
        is_api_provider = provider in ("openai", "ollama")
        
        # Для API провайдеров импортируем специфичные исключения
        if is_api_provider:
            from openai import BadRequestError, RateLimitError
            api_exceptions = (BadRequestError, RateLimitError)
        else:
            # Для HuggingFace используем общие исключения
            api_exceptions = Exception
        
        # Пробуем создать хранилище стандартным способом
        try:
            return InMemoryVectorStore.from_documents(documents, embedding=self._embeddings)
        except api_exceptions as e:
            # Если получили ошибку, пробуем добавлять документы батчами с задержками
            logger.warning(
                "Ошибка при создании эмбеддингов для всех документов: %s. "
                "Пробую добавлять документы батчами с задержками...",
                e
            )
            
            vector_store = InMemoryVectorStore(embedding=self._embeddings)
            successful_count = 0
            failed_count = 0
            
            # Размер батча и задержка между запросами
            # Для HuggingFace (локальные модели) задержки не нужны
            # Для API (OpenAI/Fireworks) задержки нужны для избежания rate limit
            if provider == "huggingface":
                batch_size = 50  # Большие батчи для локальных моделей
                delay_between_requests = 0.0  # Нет задержек для локальных моделей
                delay_after_rate_limit = 0.0  # Rate limit не применим
            else:
                batch_size = 5  # Меньшие батчи для API
                delay_between_requests = 0.5  # 500ms между запросами (увеличено для Fireworks API)
                delay_after_rate_limit = 5.0  # 5 секунд после rate limit ошибки
            
            for batch_start in range(0, len(documents), batch_size):
                batch = documents[batch_start:batch_start + batch_size]
                
                for idx, doc in enumerate(batch):
                    doc_idx = batch_start + idx + 1
                    max_retries = 3
                    retry_count = 0
                    success = False
                    
                    while retry_count < max_retries and not success:
                        try:
                            vector_store.add_documents([doc])
                            successful_count += 1
                            success = True
                            
                            # Небольшая задержка между успешными запросами (только для API)
                            if doc_idx < len(documents) and delay_between_requests > 0:
                                time.sleep(delay_between_requests)
                        
                        except Exception as exc:
                            # Обработка rate limit только для API провайдеров
                            if is_api_provider:
                                try:
                                    from openai import RateLimitError, BadRequestError
                                    
                                    if isinstance(exc, RateLimitError):
                                        retry_count += 1
                                        if retry_count < max_retries and delay_after_rate_limit > 0:
                                            logger.warning(
                                                "Rate limit достигнут для чанка #%s. Ожидание %s секунд...",
                                                doc_idx,
                                                delay_after_rate_limit
                                            )
                                            time.sleep(delay_after_rate_limit)
                                        else:
                                            failed_count += 1
                                            logger.warning(
                                                "Пропущен чанк #%s из-за rate limit после %s попыток",
                                                doc_idx,
                                                max_retries
                                            )
                                        continue
                                    
                                    if isinstance(exc, BadRequestError):
                                        failed_count += 1
                                        logger.warning(
                                            "Пропущен проблемный чанк #%s из %s (длина: %s символов): %s",
                                            doc_idx,
                                            doc.metadata.get("source", "unknown"),
                                            len(doc.page_content),
                                            doc.page_content[:100] + "..." if len(doc.page_content) > 100 else doc.page_content
                                        )
                                        success = True
                                        continue
                                except ImportError:
                                    pass
                            
                            # Общие ошибки (для HuggingFace или других провайдеров)
                            failed_count += 1
                            logger.warning(
                                "Ошибка при обработке чанка #%s: %s",
                                doc_idx,
                                exc
                            )
                            success = True  # Помечаем как обработанный, даже если не добавлен
                
                # Логируем прогресс каждые 50 чанков
                if (batch_start + batch_size) % 50 == 0:
                    logger.info(
                        "Прогресс индексации: %s/%s чанков обработано (успешно: %s, пропущено: %s)",
                        min(batch_start + batch_size, len(documents)),
                        len(documents),
                        successful_count,
                        failed_count
                    )
            
            if failed_count > 0:
                logger.info(
                    "Индексация завершена с пропусками: успешно %s, пропущено %s из %s чанков",
                    successful_count,
                    failed_count,
                    len(documents)
                )
            
            if successful_count == 0:
                raise ValueError("Не удалось проиндексировать ни одного чанка из-за ошибок")
            
            return vector_store


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    """Возвращает клиент эмбеддингов в зависимости от провайдера."""
    provider = config.EMBEDDINGS_PROVIDER.lower()

    if provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        return OpenAIEmbeddings(
            model=config.EMBEDDINGS_MODEL,
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL,
        )
    elif provider == "huggingface":
        from langchain_huggingface import HuggingFaceEmbeddings
        import os

        # Настраиваем переменные окружения для использования кэша
        if config.HUGGINGFACE_CACHE_FOLDER:
            cache_path = Path(config.HUGGINGFACE_CACHE_FOLDER).expanduser().resolve()
            # Устанавливаем переменные окружения для HuggingFace
            os.environ["HF_HOME"] = str(cache_path)
            os.environ["TRANSFORMERS_CACHE"] = str(cache_path / "transformers")
            os.environ["HF_DATASETS_CACHE"] = str(cache_path / "datasets")
            logger.info("Используется кэш HuggingFace: %s", cache_path)

        model_kwargs = {"device": config.HUGGINGFACE_DEVICE}
        encode_kwargs = {"normalize_embeddings": config.HUGGINGFACE_NORMALIZE_EMBEDDINGS}

        kwargs = {
            "model_name": config.EMBEDDINGS_MODEL,
            "model_kwargs": model_kwargs,
            "encode_kwargs": encode_kwargs,
        }

        if config.HUGGINGFACE_CACHE_FOLDER:
            kwargs["cache_folder"] = str(cache_path)

        return HuggingFaceEmbeddings(**kwargs)
    elif provider == "ollama":
        from langchain_ollama import OllamaEmbeddings

        return OllamaEmbeddings(model=config.EMBEDDINGS_MODEL)
    else:
        raise ValueError(
            f"Неподдерживаемый провайдер эмбеддингов: {provider}. "
            "Поддерживаются: openai, huggingface, ollama"
        )


@lru_cache(maxsize=1)
def get_vector_store_manager() -> VectorStoreManager:
    """Глобальный менеджер in-memory хранилища."""
    return VectorStoreManager(embeddings=get_embeddings())

