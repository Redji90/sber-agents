# src/app/config.py
import os
import logging
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Загружаем переменные из .env файла с обработкой ошибок кодировки
# Используем override=True, чтобы переменные из .env имели приоритет над системными
try:
    load_dotenv(override=True)
except UnicodeDecodeError as e:
    logger.warning(
        "Ошибка кодировки UTF-8 при чтении .env файла: %s. "
        "Пробую загрузить с кодировкой cp1251...",
        e
    )
    # Пробуем загрузить с альтернативной кодировкой (cp1251 для Windows)
    try:
        load_dotenv(override=True, encoding="cp1251")
        logger.info("Файл .env успешно загружен с кодировкой cp1251")
    except Exception as fallback_error:
        logger.warning(
            "Не удалось загрузить .env файл ни с UTF-8, ни с cp1251: %s. "
            "Переменные окружения из системы будут использованы.",
            fallback_error
        )
except Exception as e:
    logger.warning(
        "Ошибка при загрузке .env файла: %s. Используются переменные окружения из системы.",
        e
    )

# Настройка LangSmith трейсинга (автоматически работает через LangChain при наличии API ключа)
# LangChain автоматически подхватывает трейсинг если установлены переменные окружения:
# - LANGCHAIN_TRACING_V2=true (или автоматически при наличии LANGCHAIN_API_KEY/LANGSMITH_API_KEY)
# - LANGCHAIN_API_KEY или LANGSMITH_API_KEY
# - LANGCHAIN_PROJECT или LANGSMITH_PROJECT (опционально)
if os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY"):
    os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
    if os.getenv("LANGSMITH_API_KEY") and not os.getenv("LANGCHAIN_API_KEY"):
        os.environ["LANGCHAIN_API_KEY"] = os.getenv("LANGSMITH_API_KEY")
    if os.getenv("LANGSMITH_PROJECT") and not os.getenv("LANGCHAIN_PROJECT"):
        os.environ["LANGCHAIN_PROJECT"] = os.getenv("LANGSMITH_PROJECT")


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Переменная окружения {name} не установлена.")
    return value


def _get_int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(f"Переменная окружения {name} должна быть целым числом.") from exc


def _get_bool_env(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.lower() in ("true", "1", "yes", "on")


# Обязательные переменные окружения
TELEGRAM_BOT_TOKEN = _get_required_env("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = _get_required_env("OPENAI_API_KEY")

# Необязательные переменные окружения с дефолтными значениями
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.fireworks.ai/inference/v1")
# Дефолтная модель - используем актуальную модель Fireworks
# Попробуйте разные варианты, если один не работает:
# - accounts/fireworks/models/llama-3.1-8b-instruct
# - accounts/fireworks/models/llama-v3p1-8b-instruct
# - accounts/fireworks/models/llama-v3-8b-instruct
# Для GigaChat используйте: GigaChat
LLM_MODEL = os.getenv("LLM_MODEL", "accounts/fireworks/models/llama-3.1-8b-instruct")

# Автокоррекция модели для Groq (если используется Groq API)
if "groq.com" in OPENAI_BASE_URL:
    # Groq не поддерживает модель llama-3.1-8b-versatile
    # Исправляем на правильную модель Groq
    if "llama-3.1-8b-versatile" in LLM_MODEL:
        logger.warning(
            "Модель 'llama-3.1-8b-versatile' не существует в Groq. "
            "Автоматически заменяем на 'openai/gpt-oss-20b'."
        )
        LLM_MODEL = "openai/gpt-oss-20b"
    elif LLM_MODEL == "accounts/fireworks/models/llama-3.1-8b-instruct":
        # Если используется дефолтная модель Fireworks, но base_url указывает на Groq
        logger.info(
            "Обнаружен Groq API, но используется модель Fireworks. "
            "Автоматически заменяем на 'openai/gpt-oss-20b'."
        )
        LLM_MODEL = "openai/gpt-oss-20b"
    # Поддержка короткого имени модели (gpt-oss-20 -> gpt-oss-20b)
    elif LLM_MODEL in ["openai/gpt-oss-20", "gpt-oss-20"]:
        logger.info(
            "Обнаружено короткое имя модели '%s'. "
            "Автоматически заменяем на 'openai/gpt-oss-20b'.",
            LLM_MODEL
        )
        LLM_MODEL = "openai/gpt-oss-20b"
# Провайдер LLM: openai (OpenAI-совместимый API) или gigachat (GigaChat от Сбера)
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
SYSTEM_ROLE = os.getenv("SYSTEM_ROLE", "банковский ассистент")
CONTEXT_TURNS = _get_int_env("CONTEXT_TURNS", 8)
# RETRIEVER_K оставлен для обратной совместимости, но рекомендуется использовать SEMANTIC_K/HYBRID_K/RERANKER_K
RETRIEVER_K = _get_int_env("RETRIEVER_K", 4)
DATA_PATH = os.getenv("DATA_PATH", "@data")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
SHOW_SOURCES = _get_bool_env("SHOW_SOURCES", False)

# LangSmith настройки (опционально, для трейсинга и evaluation)
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY") or os.getenv("LANGCHAIN_API_KEY")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT") or os.getenv("LANGCHAIN_PROJECT")

# RAGAS настройки (опционально, для evaluation метрик)
# Модель LLM для RAGAS (если не указана или пустая, используется LLM_MODEL)
_ragas_llm_model = os.getenv("RAGAS_LLM_MODEL")
RAGAS_LLM_MODEL = _ragas_llm_model if _ragas_llm_model else LLM_MODEL
# Отдельный base_url для RAGAS (если не указан, используется OPENAI_BASE_URL)
# Полезно для использования другого провайдера для evaluation (например, LLMost вместо Groq)
RAGAS_OPENAI_BASE_URL = os.getenv("RAGAS_OPENAI_BASE_URL") or OPENAI_BASE_URL
# Отдельный API key для RAGAS (если не указан, используется OPENAI_API_KEY)
RAGAS_OPENAI_API_KEY = os.getenv("RAGAS_OPENAI_API_KEY") or OPENAI_API_KEY
# По умолчанию используем huggingface для RAGAS (лучшая совместимость)
RAGAS_EMBEDDINGS_PROVIDER = os.getenv("RAGAS_EMBEDDINGS_PROVIDER", "huggingface")
# Провайдер эмбеддингов для основной системы (openai/huggingface/ollama)
# По умолчанию используется ollama для совместимости с текущей реализацией
EMBEDDINGS_PROVIDER = os.getenv("EMBEDDINGS_PROVIDER", "ollama")

# Модель эмбеддингов (зависит от провайдера)
# Если не указана, выбирается автоматически в зависимости от провайдера
_embeddings_model = os.getenv("EMBEDDINGS_MODEL")
if _embeddings_model:
    EMBEDDINGS_MODEL = _embeddings_model
else:
    # Дефолтные модели в зависимости от провайдера
    if EMBEDDINGS_PROVIDER == "ollama":
        EMBEDDINGS_MODEL = "nomic-embed-text"
    elif EMBEDDINGS_PROVIDER == "huggingface":
        EMBEDDINGS_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    else:  # openai
        EMBEDDINGS_MODEL = "accounts/fireworks/models/nomic-embed-text-v1"

# RAGAS модель эмбеддингов (зависит от RAGAS_EMBEDDINGS_PROVIDER)
# Если не указана явно, выбирается автоматически в зависимости от RAGAS_EMBEDDINGS_PROVIDER
# Если RAGAS_EMBEDDINGS_PROVIDER совпадает с EMBEDDINGS_PROVIDER, используется EMBEDDINGS_MODEL
_ragas_embedding_model = os.getenv("RAGAS_EMBEDDING_MODEL")
if _ragas_embedding_model:
    RAGAS_EMBEDDING_MODEL = _ragas_embedding_model
else:
    # Если RAGAS_EMBEDDINGS_PROVIDER совпадает с EMBEDDINGS_PROVIDER, используем EMBEDDINGS_MODEL
    if RAGAS_EMBEDDINGS_PROVIDER.lower() == EMBEDDINGS_PROVIDER.lower():
        RAGAS_EMBEDDING_MODEL = EMBEDDINGS_MODEL
    else:
        # Дефолтные модели в зависимости от RAGAS_EMBEDDINGS_PROVIDER
        if RAGAS_EMBEDDINGS_PROVIDER.lower() == "huggingface":
            # Используем ту же модель, что и для основных embeddings, если она HuggingFace
            if EMBEDDINGS_PROVIDER.lower() == "huggingface":
                RAGAS_EMBEDDING_MODEL = EMBEDDINGS_MODEL
            else:
                RAGAS_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        else:  # openai (по умолчанию для RAGAS)
            RAGAS_EMBEDDING_MODEL = "accounts/fireworks/models/nomic-embed-text-v1"

# HuggingFace настройки (опционально, для локальных моделей)
# Устройство для HuggingFace моделей (cpu/cuda)
HUGGINGFACE_DEVICE = os.getenv("HUGGINGFACE_DEVICE", "cpu")
# Папка для кэширования HuggingFace моделей (None = использовать дефолтный кэш)
HUGGINGFACE_CACHE_FOLDER = os.getenv("HUGGINGFACE_CACHE_FOLDER") or None
# Нормализация эмбеддингов для HuggingFace (true/false)
HUGGINGFACE_NORMALIZE_EMBEDDINGS = _get_bool_env("HUGGINGFACE_NORMALIZE_EMBEDDINGS", True)

# Настройки для evaluation (параллельная обработка)
# Количество одновременных запросов при evaluation (больше = быстрее, но больше нагрузка на API)
EVALUATION_MAX_CONCURRENT = int(os.getenv("EVALUATION_MAX_CONCURRENT", "1"))
# Задержка между запросами в секундах (для избежания rate limits)
EVALUATION_DELAY_BETWEEN_REQUESTS = float(os.getenv("EVALUATION_DELAY_BETWEEN_REQUESTS", "2.0"))
# Усиленные ограничения для Groq (6000 TPM, строгие лимиты даже на on_demand tier)
if "groq.com" in OPENAI_BASE_URL:
    if EVALUATION_MAX_CONCURRENT > 1:
        logger.warning(
            "Groq имеет строгие rate limits (TPM=6000). "
            "EVALUATION_MAX_CONCURRENT понижен с %s до 1.",
            EVALUATION_MAX_CONCURRENT,
        )
        EVALUATION_MAX_CONCURRENT = 1
    if EVALUATION_DELAY_BETWEEN_REQUESTS < 3.0:
        logger.warning(
            "Groq требует большую задержку между запросами во время evaluation. "
            "EVALUATION_DELAY_BETWEEN_REQUESTS увеличен до 3.0 секунд."
        )
        EVALUATION_DELAY_BETWEEN_REQUESTS = 3.0
# Максимальное количество примеров для обработки (0 = без ограничений, для тестирования можно ограничить)
EVALUATION_MAX_EXAMPLES = int(os.getenv("EVALUATION_MAX_EXAMPLES", "0"))
# Оптимизация RAGAS: использовать только основные метрики для ускорения (true/false)
# Если True, вычисляются только faithfulness, answer_relevancy, answer_similarity (быстрее)
# Если False, вычисляются все 6 метрик (медленнее, но полнее)
EVALUATION_FAST_MODE = _get_bool_env("EVALUATION_FAST_MODE", False)

# Advanced RAG настройки (опционально, для hybrid retrieval и reranking)
# Режим работы RAG pipeline (semantic/hybrid/hybrid+reranker)
# semantic - только семантический поиск по эмбеддингам
# hybrid - комбинация semantic search и BM25 (keyword-based поиск)
# hybrid+reranker - hybrid retrieval с дополнительной ранжировкой через Cross-Encoder
RAG_MODE = os.getenv("RAG_MODE", "semantic").lower()
if RAG_MODE not in ("semantic", "hybrid", "hybrid+reranker"):
    raise ValueError(
        f"Недопустимое значение RAG_MODE: {RAG_MODE}. "
        "Допустимые значения: semantic, hybrid, hybrid+reranker"
    )

# Количество документов для semantic retrieval (топ-K по семантическому сходству)
SEMANTIC_K = _get_int_env("SEMANTIC_K", RETRIEVER_K if RETRIEVER_K == 4 else 4)

# Количество документов для BM25 retrieval (топ-K по keyword-based поиску)
BM25_K = _get_int_env("BM25_K", RETRIEVER_K if RETRIEVER_K == 4 else 4)

# Финальное количество документов после объединения semantic и BM25 в hybrid режиме
HYBRID_K = _get_int_env("HYBRID_K", RETRIEVER_K if RETRIEVER_K == 4 else 4)

# Финальное количество документов после reranking в hybrid+reranker режиме
RERANKER_K = _get_int_env("RERANKER_K", RETRIEVER_K if RETRIEVER_K == 4 else 4)

# Модель Cross-Encoder для reranking (по умолчанию ms-marco-MiniLM-L-6-v2)
# Популярные модели:
#   CrossEncoder/ms-marco-MiniLM-L-6-v2 (быстрая, хорошее качество)
#   CrossEncoder/ms-marco-MiniLM-L-12-v2 (лучше качество, медленнее)
#   cross-encoder/ms-marco-MiniLM-L-6-v2 (альтернативный путь)
CROSSENCODER_MODEL = os.getenv("CROSSENCODER_MODEL", "CrossEncoder/ms-marco-MiniLM-L-6-v2")

# Провайдер для Cross-Encoder (по умолчанию huggingface)
# Поддерживается только huggingface (модели из sentence-transformers)
CROSSENCODER_PROVIDER = os.getenv("CROSSENCODER_PROVIDER", "huggingface").lower()
if CROSSENCODER_PROVIDER not in ("huggingface",):
    raise ValueError(
        f"Недопустимое значение CROSSENCODER_PROVIDER: {CROSSENCODER_PROVIDER}. "
        "Поддерживается только: huggingface"
    )
