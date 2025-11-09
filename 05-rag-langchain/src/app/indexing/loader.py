"""Загрузчик и разбиение PDF-документов для индексации."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence

from langchain_core.documents import Document
from langchain_community.document_loaders import JSONLoader, PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.app import config

logger = logging.getLogger(__name__)

CHUNK_SIZE = 600
CHUNK_OVERLAP = 120
JSON_FILENAME = "sberbank_help_documents.json"


def _load_pdf_documents(data_path: Path) -> list[Document]:
    if not data_path.exists():
        raise FileNotFoundError(f"Директория с данными {data_path!s} не найдена.")
    if not data_path.is_dir():
        raise NotADirectoryError(f"DATA_PATH {data_path!s} должен быть директорией.")

    loader = PyPDFDirectoryLoader(str(data_path))
    documents = loader.load()
    logger.info("Загружено %s PDF-документов для индексации.", len(documents))
    return documents


def _load_json_documents(data_path: Path, filename: str = JSON_FILENAME) -> list[Document]:
    json_path = data_path / filename
    if not json_path.exists():
        logger.info("JSON файл %s не найден. Пропускаем загрузку FAQ.", json_path)
        return []

    loader = JSONLoader(
        file_path=str(json_path),
        jq_schema=".[].full_text",
        text_content=False,
    )
    documents = loader.load()
    for document in documents:
        document.page_content = (
            document.page_content.replace("\xa0", " ").replace("\u202f", " ")
        )
        document.metadata.setdefault("source", str(json_path))
        document.metadata.setdefault("document_type", "json_qa")
    logger.info("Загружено %s записей из JSON %s.", len(documents), json_path.name)
    return documents  # type: ignore[return-value]


def _split_documents(documents: Sequence[Document]) -> list[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=[
            "\n\n\n",
            "\n\n",
            "\n",
            ". ",
            " ",
            "",
        ],
        keep_separator=True,
    )
    chunks = splitter.split_documents(list(documents))
    logger.info("Документы разбиты на %s чанков.", len(chunks))
    return chunks


def load_and_prepare_documents() -> list[Document]:
    """Загружает PDF и JSON-документы из DATA_PATH и подготавливает их к индексации."""
    data_path = Path(config.DATA_PATH)
    pdf_documents = _load_pdf_documents(data_path)
    pdf_chunks = _split_documents(pdf_documents) if pdf_documents else []

    json_documents = _load_json_documents(data_path)
    json_chunks = _split_documents(json_documents) if json_documents else []

    if not pdf_chunks and not json_chunks:
        logger.warning("В директории %s не найдено данных для индексации.", data_path)
        return []

    combined = pdf_chunks + json_chunks
    logger.info(
        "Всего документов для индексации: %s (PDF-чункы: %s, JSON-записи: %s).",
        len(combined),
        len(pdf_chunks),
        len(json_chunks),
    )
    return combined

