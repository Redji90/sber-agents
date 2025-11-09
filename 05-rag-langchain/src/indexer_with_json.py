import json
import logging
from pathlib import Path
from typing import Iterable, Optional

from langchain_community.document_loaders import JSONLoader, PyPDFLoader
from langchain_community.vectorstores import InMemoryVectorStore
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_ollama import OllamaEmbeddings

logger = logging.getLogger(__name__)

try:
    from config import config as legacy_config  # type: ignore
except ImportError:  # pragma: no cover
    legacy_config = None

if legacy_config is not None:
    DATA_PATH = Path(getattr(legacy_config, "DATA_DIR", getattr(legacy_config, "DATA_PATH", "@data")))
    EMBEDDING_MODEL = getattr(
        legacy_config,
        "EMBEDDING_MODEL",
        getattr(legacy_config, "EMBEDDINGS_MODEL", "accounts/fireworks/models/nomic-embed-text-v1"),
    )
else:
    from src.app import config as app_config

    DATA_PATH = Path(getattr(app_config, "DATA_PATH", "@data"))
    EMBEDDING_MODEL = getattr(app_config, "EMBEDDINGS_MODEL", "accounts/fireworks/models/nomic-embed-text-v1")

DEFAULT_JSON_EXPORT = Path("reports/chunks.json")


def load_pdf_documents(data_dir: Path) -> list[Document]:
    """Загружает все PDF-документы из указанной директории."""
    documents: list[Document] = []
    if not data_dir.exists():
        logger.warning("Directory %s does not exist", data_dir)
        return documents

    pdf_files = sorted(data_dir.glob("*.pdf"))
    logger.info("Found %s PDF files in %s", len(pdf_files), data_dir)

    for pdf_file in pdf_files:
        loader = PyPDFLoader(str(pdf_file))
        documents.extend(loader.load())
        logger.info("Loaded %s", pdf_file.name)

    return documents


def load_json_documents(json_file_path: str) -> list[Document]:
    """
    Загрузка документов из JSON файла с вопросами-ответами.
    Каждая пара Q&A становится отдельным чанком.
    """
    json_path = Path(json_file_path)
    if not json_path.exists():
        logger.warning("JSON file %s does not exist", json_file_path)
        return []

    loader = JSONLoader(
        file_path=str(json_path),
        jq_schema=".[].full_text",
        text_content=False,
    )

    documents = loader.load()
    logger.info("Loaded %s Q&A pairs from JSON", len(documents))
    return documents  # type: ignore[return-value]


def split_documents(pages: Iterable[Document]) -> list[Document]:
    """Разбивает документы на чанки фиксированного размера."""
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = splitter.split_documents(list(pages))
    logger.info("Split into %s chunks", len(chunks))
    return chunks


def save_chunks_to_json(chunks: Iterable[Document], output_path: Path) -> Path:
    """Сохраняет чанк-данные в JSON (контент + метаданные)."""
    output_path.parent.mkdir(parents=True, exist_ok=True)

    serializable = [
        {
            "id": index,
            "content": chunk.page_content,
            "metadata": chunk.metadata,
        }
        for index, chunk in enumerate(chunks, start=1)
    ]

    with output_path.open("w", encoding="utf-8") as file:
        json.dump(serializable, file, ensure_ascii=False, indent=2)

    logger.info("Saved chunk metadata to %s", output_path)
    return output_path


def create_vector_store(chunks: list[Document]) -> InMemoryVectorStore:
    """Создаёт in-memory векторное хранилище на базе OpenAIEmbeddings."""
    embeddings = OllamaEmbeddings(model=EMBEDDING_MODEL)
    vector_store = InMemoryVectorStore.from_documents(chunks, embedding=embeddings)
    logger.info("Created vector store with %s chunks", len(chunks))
    return vector_store


async def reindex_all(
    save_json: bool = False,
    json_path: Optional[Path] = None,
    json_filename: str = "sberbank_help_documents.json",
) -> Optional[InMemoryVectorStore]:
    """Полная переиндексация всех документов (PDF + JSON)."""
    logger.info("Starting full reindexing with JSON export=%s ...", save_json)

    try:
        pdf_pages = load_pdf_documents(DATA_PATH)
        if not pdf_pages:
            logger.warning("No PDF documents found to index")

        pdf_chunks = split_documents(pdf_pages) if pdf_pages else []

        json_file = DATA_PATH / json_filename
        json_chunks = load_json_documents(str(json_file))

        all_chunks = pdf_chunks + json_chunks

        if not all_chunks:
            logger.warning("No documents found to index")
            return None

        logger.info(
            "Total chunks to index: %s (PDF: %s, JSON: %s)",
            len(all_chunks),
            len(pdf_chunks),
            len(json_chunks),
        )

        if save_json:
            target_path = json_path or DEFAULT_JSON_EXPORT
            save_chunks_to_json(all_chunks, target_path)

        vector_store = create_vector_store(all_chunks)
        logger.info("Reindexing completed successfully")
        return vector_store

    except FileNotFoundError as error:
        logger.error("File not found: %s", error)
        return None
    except Exception as error:  # pragma: no cover
        logger.error("Error during reindexing: %s", error, exc_info=True)
        return None

