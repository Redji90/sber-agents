## Техническое видение (MVP)

Этот документ конкретизирует идею из `docs/idea.md` для реализации минимально жизнеспособного прототипа (KISS, YAGNI).

### Технологии
- Язык: Python 3.11
- Управление зависимостями: `uv`
- Сборка/утилиты: `make` (задачи: установка, запуск бота, формат/линт)
- Telegram Bot API: `aiogram` 3.x, режим `polling`
- LangChain: цепочки, retriever, InMemoryVectorStore
- LLM и эмбеддинги: Fireworks AI через совместимый `openai`-клиент (настройки из `.env`)
- Модель для генерации и модель эмбеддингов задаются через `.env`
- Логирование: стандартный `logging` (уровень `INFO`)
- Контекст диалога и история сообщений: хранение в памяти процесса в формате LangChain messages

### Принцип разработки
- Минимум функционала для проверки гипотезы (KISS, YAGNI).
- Итеративная разработка маленькими инкрементами.
- Простой trunk-based workflow (ветка `main`, короткие feature-ветки).
- Единообразие кода: `ruff` (линт) и `black` (формат) через `make`.
- Минимум тестов: smoke-тест запуска, проверка конфигурации и базовой команды.
- Документация рядом с кодом: `README`, `docs/*` кратко и по делу.
### Структура проекта

```text
03-aidd/
  Makefile
  pyproject.toml
  .env.example
  docs/
    idea.md
    vision.md
  src/
    app/
      __init__.py
      config.py         # загрузка конфигурации из env
      logging.py        # базовая настройка logging
      memory/
        __init__.py
        session.py      # память процесса: последние N реплик в формате LangChain messages
      indexing/
        __init__.py
        loader.py       # чтение PDF, разбиение на чанки, создание документов
        vector_store.py # in-memory векторное хранилище, статус индексации
      rag/
        __init__.py
        chain.py        # построение rag_query_transform_chain
      llm/
        __init__.py
        client.py       # обёртка над OpenAI-совместимым клиентом (Fireworks)
      bot/
        __init__.py
        handlers.py     # обработчики команд и сообщений (включая /index, /index_status)
        main.py         # точка входа бота (aiogram polling)
```

Переменные окружения:
- `TELEGRAM_BOT_TOKEN`
- `OPENAI_API_KEY`
- `OPENAI_BASE_URL=https://api.fireworks.ai/inference/v1`
- `LLM_MODEL=accounts/fireworks/models/llama-v3p1-8b-instruct`
- `EMBEDDINGS_MODEL=accounts/fireworks/models/nomic-embed-text-v1` (пример)
- `SYSTEM_ROLE=банковский ассистент`
- `CONTEXT_TURNS=8`
- `RETRIEVER_K=4`
- `DATA_PATH=@data`
- `LOG_LEVEL=INFO`

### Архитектура проекта

```
┌─────────────────────────────────┐
│  bot/main.py                   │  ← точка входа, запуск polling
│  - создаёт Bot, Dispatcher     │
│  - регистрирует handlers       │
│  - инициирует переиндексацию   │
│  - запускает polling           │
└─────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  bot/handlers.py               │  ← обработчики команд и сообщений
│  - /start, /help, /reset       │
│  - /index, /index_status       │
│  - текстовые сообщения (RAG)   │
│  - используют memory, rag chain│
└─────────────────────────────────┘
           │
      ┌────┼─────────┐
      ▼    ▼         ▼
┌──────────┐  ┌──────────────┐   ┌───────────────┐
│ indexing │  │ memory/      │   │ rag/chain.py  │
│ loader + │  │ session.py   │   │               │
│ vector   │  │ - хранит     │   │ - query       │
│ store    │  │   ιστοpию    │   │   transform   │
│ - PDF    │  │   LangChain   │  │ - retrieval   │
│ - чанки  │  │   messages   │   │ - генерация   │
└──────────┘  └──────────────┘   └───────────────┘
           │              │               │
           ▼              ▼               ▼
        InMemoryVectorStore           llm/client.py

Конфигурация (config.py):
- читает .env
- предоставляет глобальные настройки

Логирование (logging.py):
- настраивает stdlib logging
- уровень INFO
```

**Принципы:**
- Линейный поток: main → handlers → llm/memory
- Нет dependency injection, нет сложных паттернов
- config.py — модуль с глобальными переменными
- Каждый модуль делает одну задачу
- Без middleware, без плагинов, без абстракций сверх MVP

### Модель данных

**Session Memory (memory/session.py):**
- Хранилище: `dict[int, list[BaseMessage]]` — список LangChain messages.
- Методы:
  - `add_message(user_id, message: BaseMessage)` — добавляет сообщение, обрезает до `CONTEXT_TURNS`.
  - `get_messages(user_id)` → список последних N сообщений.
  - `clear_session(user_id)` — очистка сессии (для команды `/reset` и при `/start`).

**RAG-цепочка:**
- `rag_query_transform_chain` (LangChain): трансформация запроса с учётом истории, retrieval, генерация ответа.
- Ретривер: InMemoryVectorStore retriever (`similarity_search` топ-K).
- Источники данных: PDF-документы загружаются через LangChain loaders (пример: `PyPDFLoader`), разбиваются на чанки.
- Метаданные чанков включают путь к источнику и номер страницы.
- Контекст формируется динамически и передаётся в модель генерации.

**Конфигурация (config.py):**
- Глобальные переменные модуля: `telegram_token`, `fireworks_api_key`, `llm_model`, `system_role`, `context_turns`, `log_level`
- Загрузка из `.env` через `python-dotenv` (опционально, можно и `os.getenv()`)

### Работа с LLM

**llm/client.py — обёртка над OpenAI-совместимым клиентом Fireworks:**
- Инициализация: `OpenAI(base_url=fireworks_base_url, api_key=fireworks_api_key)`
- Метод `generate(messages: list[BaseMessage]) -> str`:
  - Конвертирует LangChain messages в формат Chat API, добавляет системный промпт.
  - Вызывает `client.chat.completions.create(model=llm_model, messages=messages)` с параметрами по умолчанию.
  - Возвращает `response.choices[0].message.content`.
- Обработка ошибок: логирование и возврат пользователю сообщения "Извините, произошла ошибка. Попробуйте позже".

**Процесс работы:**
1. Handler получает сообщение пользователя
2. Берёт историю из Session Memory: `get_messages(user_id)`
3. Добавляет новое сообщение пользователя в память
4. Вызывает `llm_client.generate(messages)` с историей
5. Сохраняет ответ бота в Session Memory
6. Отправляет ответ пользователю в Telegram

### Сценарии работы

**1. Запуск бота:**
- При старте приложения инициируется переиндексация (очистка и загрузка документов).
- Статус индекса обновляется на время процедуры.

**2. Команда /start:**
- Приветственное сообщение: "Привет! Я банковский ассистент. Задавайте вопросы, и я помогу вам."
- Очистка сессии пользователя.

**2. Команда /help:**
- Сообщение: "Я банковский ассистент. Задавайте вопросы, и я отвечу на них."

**3. Команда /reset:**
- Очистка истории диалога пользователя через `clear_session(user_id)`.
- Подтверждение: "История диалога очищена. Начинаем с чистого листа."

**4. Команда /index:**
- Запускает переиндексацию: очистка in-memory векторной базы, загрузка PDF, разбиение на чанки, генерация эмбеддингов, обновление хранения.
- Отвечает пользователю, что индекс обновляется.

**5. Команда /index_status:**
- Возвращает пользователю текущий статус (например, `running`/`ready`) и количество доступных чанков.

**6. Текстовое сообщение пользователя:**
- Добавление нового сообщения в Session Memory (HumanMessage).
- Отправка индикатора "печатает..." через `bot.send_chat_action("typing")`.
- Применение `rag_query_transform_chain`: трансформация запроса, извлечение топ-K чанков, подготовка контекста.
- Вызов LLM через `llm_client.generate(...)` с историей и контекстом.
- Сохранение ответа (AIMessage) в Session Memory.
- Отправка ответа пользователю.
- Логирование основных шагов (user_id, длина сообщения, время ответа).

**5. Ошибка при обращении к LLM:**
- Отдельная обработка ошибок сети/таймаутов с логированием деталей
- Отправка пользователю: "Извините, произошла ошибка. Попробуйте позже."

**6. Слишком длинное сообщение:**
- Для MVP можно не ограничивать, но логировать предупреждение, если сообщение превышает разумный лимит (например, 4000 символов)

### Подход к конфигурированию

- **config.py:**
- Загрузка переменных окружения через `python-dotenv` (поддержка `.env` файла)
- Глобальные переменные модуля: `telegram_token`, `openai_api_key`, `openai_base_url`, `llm_model`, `system_role`, `context_turns`, `log_level`
- Обязательные переменные: `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY` — остальные с дефолтами
- Валидация при импорте модуля: проверка обязательных переменных, выброс исключения с понятным сообщением, если чего-то не хватает
- Значения по умолчанию:
  - `OPENAI_BASE_URL=https://api.fireworks.ai/inference/v1`
  - `LLM_MODEL=accounts/fireworks/models/llama-v3p1-8b-instruct`
  - `SYSTEM_ROLE=банковский ассистент`
- `CONTEXT_TURNS=8`
- `RETRIEVER_K=4`
- `DATA_PATH=@data`
- `LOG_LEVEL=INFO`

**.env.example:**
- Шаблон с примерами всех переменных окружения
- Комментарии для понимания назначения каждой переменной

### Подход к логгированию

**logging.py:**
- Стандартный `logging` (stdlib)
- Формат: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- Уровень: из `LOG_LEVEL` (по умолчанию `INFO`)
- Вывод: в консоль (stdout), без файлов на MVP

**Что логировать:**
- Запуск/остановка бота (`INFO`)
- Команды пользователей (`INFO`: user_id, команда)
- Текстовые сообщения (`INFO`: user_id, длина сообщения; без содержания)
- Запросы к LLM (`INFO`: user_id, время ответа)
- Ошибки (`ERROR`: детали с traceback)
- Предупреждения (`WARNING`: например, слишком длинное сообщение)