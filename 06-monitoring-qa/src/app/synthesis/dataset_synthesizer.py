"""Модуль синтеза Q&A датасетов из PDF документов для evaluation."""
from __future__ import annotations

import json
import logging
from collections import defaultdict
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from src.app import config
from src.app.indexing.loader import _load_pdf_documents, _split_documents

logger = logging.getLogger(__name__)

DATASET_FILENAME = "06-rag-qa-dataset.json"
CHUNKS_PER_PDF = 6  # Количество чанков для выборки из каждого PDF (увеличено для большего количества записей из PDF)
MAX_JSON_QA = 8  # Максимальное количество Q&A из JSON
MAX_TOTAL_QA = 20  # Максимальное общее количество записей в датасете


def _sample_chunks_per_pdf(chunks: list[Document], chunks_per_pdf: int = CHUNKS_PER_PDF) -> list[Document]:
    """Выбирает по chunks_per_pdf чанков из каждого PDF."""
    chunks_by_source: dict[str, list[Document]] = defaultdict(list)

    for chunk in chunks:
        source = chunk.metadata.get("source", "unknown")
        chunks_by_source[source].append(chunk)

    selected_chunks = []
    for source, source_chunks in chunks_by_source.items():
        # Выбираем первые chunks_per_pdf чанков из каждого PDF
        selected = source_chunks[:chunks_per_pdf]
        selected_chunks.extend(selected)
        logger.info(
            "Выбрано %s чанков из %s (всего %s чанков в файле)",
            len(selected),
            Path(source).name,
            len(source_chunks),
        )

    return selected_chunks


def _generate_qa_pair(chunk: Document, llm: ChatOpenAI) -> dict[str, Any] | None:
    """Генерирует пару вопрос-ответ из чанка через LLM."""
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                "Ты помощник для создания тестового датасета. "
                "На основе предоставленного фрагмента документа создай один вопрос и эталонный ответ. "
                "Вопрос должен быть конкретным и относящимся к содержимому фрагмента. "
                "Ответ должен быть кратким, но полным.",
            ),
            (
                "human",
                "Фрагмент документа:\n{content}\n\n"
                "Создай JSON объект с полями 'question' и 'answer'. "
                "Вопрос должен быть на русском языке и относиться к содержимому. "
                "Ответ должен быть основан на информации из фрагмента.",
            ),
        ]
    )

    try:
        chain = prompt | llm
        response = chain.invoke({"content": chunk.page_content})
        response_text = response.content.strip()

        # Пытаемся извлечь JSON из ответа
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            response_text = response_text[json_start:json_end].strip()

        qa_data = json.loads(response_text)

        return {
            "question": qa_data.get("question", ""),
            "answer": qa_data.get("answer", ""),
            "contexts": [chunk.page_content],
            "ground_truths": [qa_data.get("answer", "")],
            "metadata": {
                "source": chunk.metadata.get("source", "unknown"),
                "page": chunk.metadata.get("page"),
            },
        }
    except Exception as exc:
        logger.warning("Ошибка при генерации Q&A для чанка: %s", exc)
        return None


def _load_existing_qa_from_json(
    data_path: Path,
    json_filename: str = "sberbank_help_documents.json",
    max_count: int | None = None,
) -> list[dict[str, Any]]:
    """Загружает готовые Q&A пары из JSON файла.
    
    Args:
        data_path: Путь к директории с данными
        json_filename: Имя JSON файла
        max_count: Максимальное количество Q&A для загрузки (None = без ограничений)
    """
    json_path = data_path / json_filename
    if not json_path.exists():
        logger.info("JSON файл %s не найден. Пропускаем загрузку готовых Q&A.", json_path)
        return []

    try:
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        qa_pairs = []
        for item in data:
            if "question" in item and "answer" in item:
                qa_pairs.append(
                    {
                        "question": item["question"],
                        "answer": item["answer"],
                        "contexts": [item.get("full_text", item["answer"])],
                        "ground_truths": [item["answer"]],
                        "metadata": {
                            "source": str(json_path),
                            "category": item.get("category"),
                            "type": item.get("type", "json_qa"),
                        },
                    }
                )
                # Ограничиваем количество, если задано
                if max_count is not None and len(qa_pairs) >= max_count:
                    break

        logger.info("Загружено %s готовых Q&A пар из JSON (лимит: %s).", len(qa_pairs), max_count or "без ограничений")
        return qa_pairs
    except Exception as exc:
        logger.warning("Ошибка при загрузке JSON файла %s: %s", json_path, exc)
        return []


def _save_dataset(dataset: list[dict[str, Any]], output_path: Path) -> Path:
    """Сохраняет датасет в JSON файл."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, ensure_ascii=False, indent=2)

    logger.info("Датасет сохранён в %s (%s записей).", output_path, len(dataset))
    return output_path


def _upload_to_langsmith(dataset: list[dict[str, Any]], dataset_name: str, overwrite: bool = True) -> bool:
    """Загружает датасет в LangSmith с возможностью перезаписи существующего."""
    if not config.LANGSMITH_API_KEY:
        logger.info("LANGSMITH_API_KEY не установлен. Пропускаем загрузку в LangSmith.")
        return False

    try:
        from langsmith import Client

        client = Client(api_key=config.LANGSMITH_API_KEY)

        # Проверяем существование датасета
        try:
            existing_dataset = client.read_dataset(dataset_name=dataset_name)
            if overwrite:
                # Удаляем старый датасет
                logger.info("Датасет '%s' уже существует. Удаляем старый датасет...", dataset_name)
                try:
                    # Удаляем все примеры из датасета
                    examples = list(client.list_examples(dataset_name=dataset_name))
                    for example in examples:
                        try:
                            client.delete_example(example.id)
                        except Exception as exc:
                            logger.warning("Не удалось удалить пример %s: %s", example.id, exc)
                    # Удаляем сам датасет
                    client.delete_dataset(dataset_name=dataset_name)
                    logger.info("Старый датасет '%s' удалён", dataset_name)
                except Exception as exc:
                    logger.warning("Ошибка при удалении старого датасета: %s. Продолжаем создание нового...", exc)
            else:
                logger.warning(
                    "Датасет '%s' уже существует в LangSmith. Пропускаем загрузку. "
                    "Используйте overwrite=True для перезаписи.",
                    dataset_name,
                )
                return False
        except Exception:
            # Датасет не существует, можно создавать
            pass

        # Создаём датасет в LangSmith
        client.create_dataset(
            dataset_name=dataset_name,
            description="Синтезированный датасет Q&A для evaluation RAG системы",
        )

        # Загружаем примеры
        for idx, example in enumerate(dataset):
            client.create_example(
                inputs={"question": example["question"]},
                outputs={"answer": example["answer"]},
                dataset_name=dataset_name,
                metadata=example.get("metadata", {}),
            )

        logger.info("Датасет '%s' успешно загружен в LangSmith (%s примеров).", dataset_name, len(dataset))
        return True

    except ImportError:
        logger.warning("langsmith не установлен. Пропускаем загрузку в LangSmith.")
        return False
    except Exception as exc:
        logger.exception("Ошибка при загрузке датасета в LangSmith: %s", exc)
        return False


def synthesize_dataset(
    data_path: str | Path | None = None,
    output_path: str | Path | None = None,
    dataset_name: str = "06-rag-qa-dataset",
    chunks_per_pdf: int = CHUNKS_PER_PDF,
    max_json_qa: int | None = MAX_JSON_QA,
    max_total_qa: int | None = MAX_TOTAL_QA,
    upload_to_langsmith: bool = True,
) -> Path:
    """Синтезирует Q&A датасет из PDF документов и загружает в LangSmith.

    Args:
        data_path: Путь к директории с PDF документами (по умолчанию config.DATA_PATH)
        output_path: Путь для сохранения JSON файла (по умолчанию datasets/06-rag-qa-dataset.json)
        dataset_name: Название датасета в LangSmith
        chunks_per_pdf: Количество чанков для выборки из каждого PDF
        max_json_qa: Максимальное количество Q&A из JSON (None = без ограничений)
        max_total_qa: Максимальное общее количество записей (None = без ограничений)
        upload_to_langsmith: Загружать ли датасет в LangSmith

    Returns:
        Path к сохранённому JSON файлу
    """
    data_path = Path(data_path or config.DATA_PATH)
    output_path = Path(output_path or f"datasets/{DATASET_FILENAME}")

    logger.info("Начало синтеза датасета из %s", data_path)

    # Загружаем PDF документы
    pdf_documents = _load_pdf_documents(data_path)
    if not pdf_documents:
        logger.warning("PDF документы не найдены в %s", data_path)
        return output_path

    # Разбиваем на чанки
    chunks = _split_documents(pdf_documents)
    logger.info("Создано %s чанков из PDF документов", len(chunks))

    # Выбираем по chunks_per_pdf чанков из каждого PDF
    selected_chunks = _sample_chunks_per_pdf(chunks, chunks_per_pdf)
    logger.info("Выбрано %s чанков для синтеза Q&A", len(selected_chunks))

    # Генерируем Q&A пары через LLM
    llm = ChatOpenAI(
        model=config.LLM_MODEL,
        temperature=0.2,
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_BASE_URL,
    )

    dataset = []
    for idx, chunk in enumerate(selected_chunks, 1):
        logger.info("Генерация Q&A %s/%s", idx, len(selected_chunks))
        qa_pair = _generate_qa_pair(chunk, llm)
        if qa_pair:
            dataset.append(qa_pair)
            # Ограничиваем общее количество, если задано
            if max_total_qa is not None and len(dataset) >= max_total_qa:
                logger.info("Достигнут лимит общего количества записей (%s). Останавливаем генерацию из PDF.", max_total_qa)
                break

    logger.info("Сгенерировано %s Q&A пар из чанков", len(dataset))

    # Загружаем готовые Q&A из JSON (если есть)
    # Ограничиваем количество из JSON, учитывая уже созданные записи
    remaining_slots = None
    if max_total_qa is not None:
        remaining_slots = max(0, max_total_qa - len(dataset))
        if max_json_qa is not None:
            remaining_slots = min(remaining_slots, max_json_qa)
    
    existing_qa = _load_existing_qa_from_json(data_path, max_count=remaining_slots)
    dataset.extend(existing_qa)

    logger.info("Итого в датасете: %s записей (синтезировано: %s, из JSON: %s)", len(dataset), len(dataset) - len(existing_qa), len(existing_qa))

    # Сохраняем датасет
    saved_path = _save_dataset(dataset, output_path)

    # Загружаем в LangSmith (если нужно)
    if upload_to_langsmith and config.LANGSMITH_API_KEY:
        _upload_to_langsmith(dataset, dataset_name)

    return saved_path


