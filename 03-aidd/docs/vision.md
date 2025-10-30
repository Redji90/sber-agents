## Техническое видение (MVP)

Этот документ конкретизирует идею из `docs/idea.md` для реализации минимально жизнеспособного прототипа (KISS, YAGNI).

### Технологии
- Язык: Python 3.11
- Управление зависимостями: `uv`
- Сборка/утилиты: `make` (задачи: установка, запуск бота, формат/линт)
- Telegram Bot API: `aiogram` 3.x, режим `polling`
- LLM-клиент: `openai` (Python) с `base_url=https://openrouter.ai/api/v1`
- Модель по умолчанию: `mistralai/mistral-7b-instruct:free` (через OpenRouter)
- Логирование: стандартный `logging` (уровень `INFO`)
- Контекст диалога: в памяти процесса (последние N реплик), без БД на MVP

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
        session.py      # память процесса: последние N реплик
      llm/
        __init__.py
        client.py       # обёртка над openai client (OpenRouter)
      bot/
        __init__.py
        handlers.py     # обработчики команд и сообщений
        main.py         # точка входа бота (aiogram polling)
```

Переменные окружения:
- `TELEGRAM_BOT_TOKEN`
- `OPENROUTER_API_KEY`
- `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`
- `LLM_MODEL=mistralai/mistral-7b-instruct:free`
- `SYSTEM_ROLE=банковский ассистент`
- `CONTEXT_TURNS=8`
- `LOG_LEVEL=INFO`

### Архитектура проекта

```
┌─────────────────────────────────┐
│  bot/main.py                   │  ← точка входа, запуск polling
│  - создаёт Bot, Dispatcher     │
│  - регистрирует handlers       │
│  - запускает polling           │
└─────────────────────────────────┘
           │
           ▼
┌─────────────────────────────────┐
│  bot/handlers.py               │  ← обработчики сообщений
│  - /start, /help               │
│  - текстовые сообщения         │
│  - использует LLM client       │
│  - использует Session memory   │
└─────────────────────────────────┘
           │
      ┌────┴────┐
      ▼         ▼
┌──────────┐  ┌──────────────┐
│ llm/     │  │ memory/      │
│ client.py│  │ session.py   │
│          │  │              │
│ - OpenAI │  │ - хранит     │
│   client │  │   последние  │
│ - OpenRouter│ │   N реплик │
│   API    │  │ - в памяти   │
└──────────┘  └──────────────┘

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
- Хранилище: `dict[int, list[dict]]` — `{user_id: [{"role": "user"/"assistant", "content": "текст"}, ...]}`
- Методы:
  - `add_message(user_id, role, content)` — добавляет сообщение, обрезает до `CONTEXT_TURNS`
  - `get_messages(user_id)` → список последних N реплик для формирования контекста LLM
  - `clear_session(user_id)` — очистка сессии (опционально, для команды /reset)

**LLM Request/Response:**
- Формат: OpenAI Chat API — `[{"role": "system", "content": "..."}, {"role": "user", "content": "..."}, ...]`
- Системный промпт: берётся из `SYSTEM_ROLE` (один раз в начале запроса)
- История: формируется из Session Memory (последние N реплик пользователя и бота)

**Конфигурация (config.py):**
- Глобальные переменные модуля: `telegram_token`, `openrouter_api_key`, `llm_model`, `system_role`, `context_turns`, `log_level`
- Загрузка из `.env` через `python-dotenv` (опционально, можно и `os.getenv()`)

### Работа с LLM

**llm/client.py — обёртка над OpenAI client:**
- Инициализация: `OpenAI(base_url=openrouter_base_url, api_key=openrouter_api_key)`
- Метод `generate(user_messages: list[dict]) -> str`:
  - Формирует список сообщений: `[{"role": "system", "content": system_role}, ...] + user_messages`
  - Вызывает `client.chat.completions.create(model=llm_model, messages=messages)` с параметрами по умолчанию (temperature, max_tokens)
  - Возвращает `response.choices[0].message.content`
- Обработка ошибок: логирование ошибки и возврат пользователю простого сообщения "Извините, произошла ошибка. Попробуйте позже"

**Процесс работы:**
1. Handler получает сообщение пользователя
2. Берёт историю из Session Memory: `get_messages(user_id)`
3. Добавляет новое сообщение пользователя в память
4. Вызывает `llm_client.generate(messages)` с историей
5. Сохраняет ответ бота в Session Memory
6. Отправляет ответ пользователю в Telegram

### Сценарии работы

**1. Команда /start:**
- Приветственное сообщение: "Привет! Я банковский ассистент. Задавайте вопросы, и я помогу вам."
- Очистка сессии пользователя (если была)

**2. Команда /help:**
- Сообщение: "Я банковский ассистент. Задавайте вопросы, и я отвечу на них."

**3. Команда /reset:**
- Очистка истории диалога пользователя через `clear_session(user_id)`
- Подтверждение: "История диалога очищена. Начинаем с чистого листа."

**4. Текстовое сообщение пользователя:**
- Получение сообщения → сохранение в Session Memory
- Отправка индикатора "печатает..." через `bot.send_chat_action("typing")`
- Формирование контекста из истории
- Запрос к LLM
- Сохранение ответа бота в Session Memory
- Отправка ответа пользователю в Telegram
- Логирование основных шагов (user_id, длина сообщения, время ответа)

**5. Ошибка при обращении к LLM:**
- Отдельная обработка ошибок сети/таймаутов с логированием деталей
- Отправка пользователю: "Извините, произошла ошибка. Попробуйте позже."

**6. Слишком длинное сообщение:**
- Для MVP можно не ограничивать, но логировать предупреждение, если сообщение превышает разумный лимит (например, 4000 символов)

### Подход к конфигурированию

**config.py:**
- Загрузка переменных окружения через `python-dotenv` (поддержка `.env` файла)
- Глобальные переменные модуля: `telegram_token`, `openrouter_api_key`, `openrouter_base_url`, `llm_model`, `system_role`, `context_turns`, `log_level`
- Обязательные переменные: `TELEGRAM_BOT_TOKEN`, `OPENROUTER_API_KEY` — остальные с дефолтами
- Валидация при импорте модуля: проверка обязательных переменных, выброс исключения с понятным сообщением, если чего-то не хватает
- Значения по умолчанию:
  - `OPENROUTER_BASE_URL=https://openrouter.ai/api/v1`
  - `LLM_MODEL=mistralai/mistral-7b-instruct:free`
  - `SYSTEM_ROLE=банковский ассистент`
  - `CONTEXT_TURNS=8`
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