"""Загрузчик и разбиение PDF-документов для индексации."""
from __future__ import annotations

import logging
import re
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


def _filter_and_clean_chunks(chunks: list[Document]) -> list[Document]:
    """Фильтрует и очищает чанки перед созданием эмбеддингов.
    
    Удаляет:
    - Пустые чанки или содержащие только пробелы
    - Слишком длинные чанки (>8000 символов - лимит для большинства embedding моделей)
    - Чанки с некорректными символами
    """
    filtered = []
    skipped_count = 0
    
    for chunk in chunks:
        text = chunk.page_content.strip()
        
        # Пропускаем пустые чанки
        if not text or len(text) == 0:
            skipped_count += 1
            continue
        
        # Пропускаем слишком длинные чанки (>8000 символов)
        # Большинство embedding моделей имеют лимит ~8000 токенов
        if len(text) > 8000:
            logger.warning(
                "Пропущен слишком длинный чанк (%s символов) из %s",
                len(text),
                chunk.metadata.get("source", "unknown"),
            )
            skipped_count += 1
            continue
        
        # Очищаем текст от проблемных символов
        # Удаляем нулевые байты и другие контрольные символы (кроме табуляций и переводов строк)
        cleaned_text = "".join(char for char in text if ord(char) >= 32 or char in "\n\t\r")
        
        # Дополнительная очистка: удаляем непечатаемые Unicode символы
        # Сохраняем только буквы, цифры, пробелы, пунктуацию и переводы строк
        cleaned_text = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]', '', cleaned_text)
        
        # Удаляем специальные символы, которые могут вызывать проблемы
        # Bullets, arrows, geometric shapes, mathematical symbols и другие спецсимволы
        # Но сохраняем базовую пунктуацию: .,;:!?-()[]"'
        # Удаляем различные варианты bullet points (Unicode точки разных видов)
        cleaned_text = re.sub(r'[\u2022\u2023\u25E6\u2043\u2219\u00B7\u25AA\u25AB\u25CF\u25CB]', ' ', cleaned_text)
        cleaned_text = re.sub(r'[\u25A0\u25A1\u25B2\u25B3\u25BC\u25BD\u25C6\u25C7\u2192\u2190\u2191\u2193]', ' ', cleaned_text)
        cleaned_text = re.sub(r'[\u21D2\u21D0\u21D1\u21D3\u25BA\u25C4]', ' ', cleaned_text)
        
        # Удаляем все оставшиеся специальные Unicode символы, кроме базовых
        # Оставляем только буквы, цифры, пробелы и базовую пунктуацию
        cleaned_text = re.sub(r'[^\w\s.,;:!?\-()\[\]"\'а-яА-ЯёЁ]', ' ', cleaned_text)
        
        # Заменяем нестандартные кавычки и тире на стандартные
        cleaned_text = cleaned_text.replace('"', '"').replace('"', '"')
        cleaned_text = cleaned_text.replace(''', "'").replace(''', "'")
        cleaned_text = cleaned_text.replace('—', '-').replace('–', '-')
        
        # Удаляем нулевые байты и другие проблемные символы ещё раз
        cleaned_text = cleaned_text.replace('\x00', '').replace('\ufffd', '')  # replacement character
        
        # Нормализуем пробелы (заменяем множественные пробелы на один)
        cleaned_text = re.sub(r' +', ' ', cleaned_text)
        cleaned_text = re.sub(r'\n\s*\n\s*\n+', '\n\n', cleaned_text)  # Максимум 2 перевода строки подряд
        
        # Удаляем пустые строки в начале и конце
        cleaned_text = cleaned_text.strip()
        
        if not cleaned_text or len(cleaned_text) == 0:
            skipped_count += 1
            continue
        
        # Проверяем, что текст содержит хотя бы один печатаемый символ
        if not re.search(r'[a-zA-Zа-яА-Я0-9]', cleaned_text):
            skipped_count += 1
            continue
        
        # Создаём новый документ с очищенным текстом
        cleaned_chunk = Document(
            page_content=cleaned_text,
            metadata=chunk.metadata.copy(),
        )
        filtered.append(cleaned_chunk)
    
    if skipped_count > 0:
        logger.info("Пропущено %s невалидных чанков. Осталось %s чанков для индексации.", skipped_count, len(filtered))
    
    return filtered


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
    
    # Фильтруем и очищаем чанки перед индексацией
    filtered_chunks = _filter_and_clean_chunks(combined)
    
    logger.info(
        "Всего документов для индексации: %s (PDF-чункы: %s, JSON-записи: %s, после фильтрации: %s).",
        len(combined),
        len(pdf_chunks),
        len(json_chunks),
        len(filtered_chunks),
    )
    return filtered_chunks

