"""Модуль для Advanced RAG: Hybrid Retrieval и Reranking."""
from __future__ import annotations

import logging
import re
from typing import Sequence

from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever
from rank_bm25 import BM25Okapi

from src.app import config

logger = logging.getLogger(__name__)


def _simple_tokenize(text: str) -> list[str]:
    """Простая токенизация текста для BM25."""
    # Удаляем знаки препинания и приводим к нижнему регистру
    text = re.sub(r"[^\w\s]", " ", text.lower())
    # Разбиваем на слова
    words = text.split()
    # Удаляем очень короткие слова (меньше 2 символов)
    return [word for word in words if len(word) >= 2]


class BM25Retriever(BaseRetriever):
    """BM25 retriever для keyword-based поиска документов."""

    def __init__(self, documents: Sequence[Document], k: int = 4):
        """Инициализирует BM25 retriever из документов.

        Args:
            documents: Список документов для индексации
            k: Количество документов для возврата при поиске
        """
        super().__init__()
        self._documents = list(documents)
        self._k = k

        # Токенизируем документы для BM25
        tokenized_docs = [_simple_tokenize(doc.page_content) for doc in self._documents]

        # Создаём BM25 индекс
        if tokenized_docs:
            self._bm25 = BM25Okapi(tokenized_docs)
            logger.info("BM25 индекс создан для %s документов.", len(self._documents))
        else:
            self._bm25 = None
            logger.warning("BM25 индекс не создан: документы отсутствуют.")

    def _get_relevant_documents(self, query: str) -> list[Document]:
        """Возвращает релевантные документы по запросу.

        Args:
            query: Поисковый запрос

        Returns:
            Список релевантных документов
        """
        if not self._bm25 or not self._documents:
            return []

        # Токенизируем запрос
        tokenized_query = _simple_tokenize(query)

        if not tokenized_query:
            return []

        # Получаем BM25 scores
        scores = self._bm25.get_scores(tokenized_query)

        # Сортируем документы по scores (в порядке убывания)
        doc_scores = list(enumerate(scores))
        doc_scores.sort(key=lambda x: x[1], reverse=True)

        # Выбираем топ-K документов
        top_k_indices = [idx for idx, _ in doc_scores[: self._k]]

        # Возвращаем соответствующие документы
        results = [self._documents[idx] for idx in top_k_indices if idx < len(self._documents)]

        logger.debug(
            "BM25 retrieval: запрос '%s', найдено %s документов (топ-%s).",
            query[:50],
            len(results),
            self._k,
        )

        return results

    async def _aget_relevant_documents(self, query: str) -> list[Document]:
        """Асинхронная версия _get_relevant_documents (не поддерживается BM25)."""
        return self._get_relevant_documents(query)


def _document_key(doc: Document) -> tuple[str, int | None]:
    """Создаёт ключ для идентификации документа по метаданным.

    Args:
        doc: Документ LangChain

    Returns:
        Кортеж (source, page) для уникальной идентификации документа
    """
    source = doc.metadata.get("source", "")
    page = doc.metadata.get("page", None)
    return (source, page)


class HybridRetriever(BaseRetriever):
    """Hybrid retriever, комбинирующий semantic search и BM25."""

    def __init__(
        self,
        semantic_retriever: BaseRetriever,
        bm25_retriever: BM25Retriever,
        k: int = 4,
    ):
        """Инициализирует Hybrid retriever.

        Args:
            semantic_retriever: Semantic retriever (InMemoryVectorStore retriever)
            bm25_retriever: BM25 retriever для keyword-based поиска
            k: Финальное количество документов после объединения
        """
        super().__init__()
        self._semantic_retriever = semantic_retriever
        self._bm25_retriever = bm25_retriever
        self._k = k

    def _get_relevant_documents(self, query: str) -> list[Document]:
        """Возвращает релевантные документы по запросу, объединяя semantic и BM25 результаты.

        Args:
            query: Поисковый запрос

        Returns:
            Список релевантных документов после объединения и дедупликации
        """
        # Получаем результаты от semantic retriever
        semantic_docs = self._semantic_retriever.get_relevant_documents(query)
        semantic_scores = {_document_key(doc): (doc, 2.0) for doc in semantic_docs}  # Вес 2.0 для semantic

        # Получаем результаты от BM25 retriever
        bm25_docs = self._bm25_retriever.get_relevant_documents(query)
        bm25_scores = {_document_key(doc): (doc, 1.0) for doc in bm25_docs}  # Вес 1.0 для BM25

        # Объединяем результаты с дедупликацией и взвешиванием
        # Документы, которые есть в обоих результатах, получают больший вес
        combined_scores: dict[tuple[str, int | None], tuple[Document, float]] = {}

        # Добавляем semantic результаты
        for key, (doc, score) in semantic_scores.items():
            combined_scores[key] = (doc, score)

        # Добавляем BM25 результаты, увеличивая вес для документов, которые уже есть
        for key, (doc, score) in bm25_scores.items():
            if key in combined_scores:
                # Документ есть в обоих результатах - увеличиваем вес
                existing_doc, existing_score = combined_scores[key]
                combined_scores[key] = (existing_doc, existing_score + score)
            else:
                # Новый документ из BM25
                combined_scores[key] = (doc, score)

        # Сортируем по весам (в порядке убывания)
        scored_docs = list(combined_scores.values())
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        # Выбираем топ-K документов
        results = [doc for doc, _ in scored_docs[: self._k]]

        logger.debug(
            "Hybrid retrieval: запрос '%s', semantic: %s, BM25: %s, объединено: %s, финальных: %s (топ-%s).",
            query[:50],
            len(semantic_docs),
            len(bm25_docs),
            len(combined_scores),
            len(results),
            self._k,
        )

        return results

    async def _aget_relevant_documents(self, query: str) -> list[Document]:
        """Асинхронная версия _get_relevant_documents."""
        # Для async версии используем async методы retriever'ов, если они поддерживаются
        semantic_docs = await self._semantic_retriever.aget_relevant_documents(query)
        bm25_docs = await self._bm25_retriever.aget_relevant_documents(query)

        # Та же логика объединения
        semantic_scores = {_document_key(doc): (doc, 2.0) for doc in semantic_docs}
        bm25_scores = {_document_key(doc): (doc, 1.0) for doc in bm25_docs}

        combined_scores: dict[tuple[str, int | None], tuple[Document, float]] = {}

        for key, (doc, score) in semantic_scores.items():
            combined_scores[key] = (doc, score)

        for key, (doc, score) in bm25_scores.items():
            if key in combined_scores:
                existing_doc, existing_score = combined_scores[key]
                combined_scores[key] = (existing_doc, existing_score + score)
            else:
                combined_scores[key] = (doc, score)

        scored_docs = list(combined_scores.values())
        scored_docs.sort(key=lambda x: x[1], reverse=True)

        results = [doc for doc, _ in scored_docs[: self._k]]

        return results


class Reranker:
    """Cross-Encoder reranker для улучшения порядка документов."""

    def __init__(self, model_name: str | None = None):
        """Инициализирует Cross-Encoder reranker.

        Args:
            model_name: Имя модели Cross-Encoder (по умолчанию из конфигурации)
        """
        self._model_name = model_name or config.CROSSENCODER_MODEL
        self._model = None
        self._provider = config.CROSSENCODER_PROVIDER.lower()

        if self._provider != "huggingface":
            raise ValueError(
                f"Недопустимый провайдер для Cross-Encoder: {self._provider}. "
                "Поддерживается только: huggingface"
            )

        logger.info("Cross-Encoder reranker будет инициализирован при первом использовании (модель: %s).", self._model_name)

    def _load_model(self) -> None:
        """Загружает Cross-Encoder модель при первом использовании."""
        if self._model is not None:
            return

        try:
            from sentence_transformers import CrossEncoder

            logger.info("Загрузка Cross-Encoder модели: %s...", self._model_name)
            self._model = CrossEncoder(self._model_name)
            logger.info("Cross-Encoder модель загружена успешно.")
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers не установлен. "
                "Установите: uv pip install sentence-transformers"
            ) from exc
        except Exception as exc:
            logger.error("Ошибка при загрузке Cross-Encoder модели: %s", exc)
            raise

    def rerank(self, query: str, documents: Sequence[Document], top_k: int | None = None) -> list[Document]:
        """Ранжирует документы по запросу с использованием Cross-Encoder.

        Args:
            query: Поисковый запрос
            documents: Список документов для ранжирования
            top_k: Количество топ-документов для возврата (по умолчанию все)

        Returns:
            Список документов, отсортированных по релевантности (в порядке убывания)
        """
        if not documents:
            return []

        # Загружаем модель при первом использовании
        self._load_model()

        # Подготавливаем пары (query, document) для Cross-Encoder
        pairs = [(query, doc.page_content) for doc in documents]

        # Получаем scores от Cross-Encoder
        scores = self._model.predict(pairs)

        # Сортируем документы по scores (в порядке убывания)
        doc_scores = list(zip(documents, scores, strict=True))
        doc_scores.sort(key=lambda x: x[1], reverse=True)

        # Выбираем топ-K документов
        if top_k is not None:
            results = [doc for doc, _ in doc_scores[:top_k]]
        else:
            results = [doc for doc, _ in doc_scores]

        logger.debug(
            "Cross-Encoder reranking: запрос '%s', ранжировано %s документов, возвращено %s (топ-%s).",
            query[:50],
            len(documents),
            len(results),
            top_k if top_k else len(results),
        )

        return results

