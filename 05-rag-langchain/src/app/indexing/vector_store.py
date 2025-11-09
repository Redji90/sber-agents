"""Управление in-memory векторным хранилищем и статусом индексации."""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Literal, Sequence
from datetime import datetime, timezone

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_ollama import OllamaEmbeddings
from langchain_community.vectorstores import InMemoryVectorStore

from src.app import config


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

    def replace_store(self, vector_store: InMemoryVectorStore, chunks: int) -> None:
        self._vector_store = vector_store
        self.finish_indexing(chunks)

    def set_status(self, state: Literal["idle", "running", "ready", "error"], chunks: int | None = None) -> None:
        self._status = IndexStatus(
            state=state,
            chunks=chunks if chunks is not None else self._status.chunks,
            updated_at=datetime.now(timezone.utc),
            error_message=self._status.error_message,
        )

    def get_retriever(self) -> BaseRetriever:
        return self._vector_store.as_retriever(search_kwargs={"k": config.RETRIEVER_K})

    def build_store_from_documents(self, documents: Sequence[Document]) -> InMemoryVectorStore:
        return InMemoryVectorStore.from_documents(documents, embedding=self._embeddings)


@lru_cache(maxsize=1)
def get_embeddings() -> Embeddings:
    """Возвращает клиент эмбеддингов на базе Ollama."""
    return OllamaEmbeddings(model=config.EMBEDDINGS_MODEL)


@lru_cache(maxsize=1)
def get_vector_store_manager() -> VectorStoreManager:
    """Глобальный менеджер in-memory хранилища."""
    return VectorStoreManager(embeddings=get_embeddings())

