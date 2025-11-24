# Sber Agents Monitoring QA Bot

RAG-ассистент в виде Telegram-бота с системой мониторинга и оценки качества.
Бот ведёт диалог с пользователем, отвечая на вопросы на основе локальной базы PDF-документов.
Включает автоматический трейсинг через LangSmith и оценку качества через RAGAS метрики.

Проект создан в рамках MVP, сфокусирован на принципах KISS и YAGNI.

## Установка

Для установки зависимостей и создания виртуального окружения используйте `make`:

```bash
make install
```

## Запуск

Перед запуском убедитесь, что у вас настроены переменные окружения (см. `.env.example`).
Запуск бота:

```bash
make run
```

## Разработка

- `make lint`: Проверка кода на соответствие стандартам (ruff).
- `make format`: Форматирование кода (black).

## Команды бота

- `/start` - Начать диалог
- `/help` - Показать справку
- `/reset` - Очистить историю диалога
- `/index` - Переиндексировать документы
- `/index_status` - Проверить статус индексации
- `/evaluate_dataset` - Запустить evaluation качества RAG pipeline (требуется LangSmith API ключ)

## Возможности

### RAG-ассистент
- Ответы на вопросы пользователя на основе PDF-документов
- История диалога с учётом контекста
- Опциональное отображение источников в ответе (настройка `SHOW_SOURCES`)

### Мониторинг
- Автоматический трейсинг всех запросов и ответов через LangSmith
- Интеграция работает автоматически при наличии `LANGSMITH_API_KEY`

### Оценка качества
- Синтез тестовых датасетов из PDF документов
- Evaluation RAG pipeline через RAGAS метрики
- 6 метрик: faithfulness, answer_relevancy, answer_correctness, answer_similarity, context_recall, context_precision
- Загрузка результатов в LangSmith

## Документация

- `docs/idea.md`: Идея проекта.
- `docs/vision.md`: Техническое видение проекта (MVP).
- `docs/conventions.md`: Правила разработки кода.
- `docs/tasklist.md`: Пошаговый план разработки.
- `docs/workflow.md`: Правила выполнения работ по тасклисту.

## Настройка

### 1. Создание .env файла

Создайте `.env` файл на основе примера:

```bash
# Windows PowerShell
Copy-Item env.example .env

# Linux/Mac
cp env.example .env
```

### 2. Обязательные переменные окружения

**Обязательно заполните только эти две переменные** в `.env`:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_openai_api_key_here
```

**Все остальные переменные опциональны** и имеют дефолтные значения:
- `SYSTEM_ROLE` - по умолчанию `"банковский ассистент"` (можно не менять)
- `EMBEDDINGS_PROVIDER` - по умолчанию `"ollama"` (можно не менять, если используете Ollama)
- `CONTEXT_TURNS` - по умолчанию `8` (можно не менять)
- `RETRIEVER_K` - по умолчанию `4` (можно не менять)
- `SHOW_SOURCES` - по умолчанию `false` (можно не менять)
- И другие настройки

### 3. Настройка LangSmith (опционально, но рекомендуется)

1. Зарегистрируйтесь на [smith.langchain.com](https://smith.langchain.com)
2. Создайте API ключ в Settings → API Keys (начинается с `lsv2_pt_...`)
3. Добавьте в `.env`:

```env
LANGSMITH_API_KEY=lsv2_pt_your_api_key_here
LANGSMITH_PROJECT=06-monitoring-qa
```

### 4. Выбор провайдера эмбеддингов

Выберите провайдер эмбеддингов в `.env`:

**OpenAI/Fireworks (по умолчанию, требует API ключ):**
```env
EMBEDDINGS_PROVIDER=openai
EMBEDDINGS_MODEL=accounts/fireworks/models/nomic-embed-text-v1
```

**HuggingFace (локальные модели, бесплатно):**
```env
EMBEDDINGS_PROVIDER=huggingface
EMBEDDINGS_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
RAGAS_EMBEDDINGS_PROVIDER=huggingface
RAGAS_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
# Опциональные настройки HuggingFace:
HUGGINGFACE_DEVICE=cpu  # Используйте "cuda" для GPU
HUGGINGFACE_NORMALIZE_EMBEDDINGS=true  # Нормализация эмбеддингов
HUGGINGFACE_CACHE_FOLDER=  # Папка для кэширования моделей (опционально)
```

**Ollama (локальный сервер):**
```env
EMBEDDINGS_PROVIDER=ollama
EMBEDDINGS_MODEL=nomic-embed-text
```
(требуется запущенный Ollama сервер)

### 5. Опциональные настройки

```env
SHOW_SOURCES=false  # Показывать ли источники в ответе
RAGAS_LLM_MODEL=    # Модель для RAGAS (по умолчанию LLM_MODEL)
RAGAS_EMBEDDING_MODEL=  # Модель эмбеддингов для RAGAS (по умолчанию EMBEDDINGS_MODEL)
RAGAS_EMBEDDINGS_PROVIDER=openai  # Провайдер для RAGAS (openai/huggingface)

# Настройки HuggingFace (для локальных моделей):
HUGGINGFACE_DEVICE=cpu  # Устройство (cpu/cuda)
HUGGINGFACE_NORMALIZE_EMBEDDINGS=true  # Нормализация эмбеддингов
HUGGINGFACE_CACHE_FOLDER=  # Папка для кэширования моделей (опционально)
```

### 6. Groq (облачный провайдер без VPN)

Подробная инструкция: `docs/groq-setup.md`.

```env
# Пример настроек для Groq
LLM_PROVIDER=openai
OPENAI_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-8b-instant
OPENAI_API_KEY=your_groq_api_key_here
RAGAS_LLM_MODEL=llama-3.1-8b-instant
```

Проверить ключ можно скриптом:

```bash
uv run python scripts/test_groq.py
```

Подробнее см. `.env.example` или `env.example`.

## Деплой на облачный сервис

Если вы хотите развернуть бота на облачном сервисе (например, для работы с Groq без VPN), см. подробную инструкцию:

- **[Деплой на Render.com с Groq](docs/deployment-render.md)** - пошаговая инструкция по развертыванию бота на Render.com для работы с Groq API без VPN

Render.com предоставляет бесплатный tier, что позволяет запустить бота без дополнительных затрат.
