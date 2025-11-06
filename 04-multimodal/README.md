# Финансовый советник Telegram-бот

LLM-based Telegram-бот для учета личных доходов и расходов.

## Функционал

- ✅ Ведение учета транзакций (дата, время, тип, сумма, категория, описание)
- ✅ Автоматическое извлечение данных из текстовых сообщений
- ✅ Обработка голосовых сообщений с транскрипцией
- ✅ Обработка изображений чеков (VLM)
- ✅ Отчет о балансе по команде `/balance`

## Технологии

- Python 3.10+
- `uv` для управления зависимостями
- `aiogram` для Telegram Bot API
- `openai` клиент для работы с LLM/VLM через OpenRouter или Ollama
- Structured output для извлечения данных

## Установка

1. Установите `uv`:
   ```bash
   pip install uv
   ```

2. Установите зависимости:
   ```bash
   make install
   ```

3. Настройте конфигурацию:
   - Скопируйте `config.yaml` и заполните необходимые параметры
   - Или создайте `.env` файл с переменными окружения:
     ```env
     TELEGRAM_BOT_TOKEN=your_bot_token
     LLM_PROVIDER=openrouter
     LLM_MODEL=anthropic/claude-3.5-sonnet
     LLM_API_KEY=your_api_key
     VLM_PROVIDER=openrouter
     VLM_MODEL=anthropic/claude-3.5-sonnet
     VLM_API_KEY=your_api_key
     SPEECH_PROVIDER=yandex
     SPEECH_API_KEY=your_yandex_speechkit_api_key
     SPEECH_FOLDER_ID=your_yandex_folder_id
     ```

## Запуск

```bash
make run
```

Или напрямую:
```bash
uv run python -m bot.main
```

## Использование

1. Отправьте `/start` для начала работы
2. Отправляйте сообщения о транзакциях:
   - Текстовые: "Купил продукты на 500 рублей"
   - Голосовые: расскажите о транзакции голосом
   - Изображения: отправьте фото чека
3. Используйте `/balance` для просмотра баланса

## Конфигурация моделей

### OpenRouter

Для использования OpenRouter установите:
```yaml
llm:
  provider: "openrouter"
  model: "anthropic/claude-3.5-sonnet"
  api_key: "your_openrouter_api_key"
```

### Ollama (локальные модели)

Для использования Ollama:
1. Установите и запустите Ollama локально
2. Установите нужную модель: `ollama pull llama3.2:latest`
3. Настройте конфигурацию:
```yaml
llm:
  provider: "ollama"
  model: "llama3.2:latest"
  base_url: "http://localhost:11434/v1"
```

## Структура проекта

```
.
├── bot/
│   ├── __init__.py
│   ├── config.py          # Конфигурация
│   ├── models.py          # Модели данных
│   ├── storage.py         # Хранение транзакций
│   ├── llm_client.py      # Клиенты LLM/VLM
│   └── main.py            # Основной файл бота
├── config.yaml            # Конфигурационный файл
├── pyproject.toml         # Зависимости
├── Makefile               # Команды сборки
└── README.md
```

## Формат данных

Транзакции хранятся в формате:
- Дата: YYYY-MM-DD
- Время: HH:MM:SS
- Тип: income (доход) / expense (расход)
- Сумма: число
- Категория: food, restaurants, taxi, education, travel, и др.
- Тип частоты: daily, periodic, one_time
- Описание: текстовое описание транзакции

## Примечания

- Данные хранятся в JSON файле (по умолчанию `data/transactions.json`)
- Для работы с изображениями требуется VLM с поддержкой vision
- Для транскрипции голоса используется Whisper API (требуется OpenAI-совместимый API)

## Дополнительная документация

- **[Анализ подходов к транскрибации голосовых сообщений](SPEECH_TO_TEXT_ANALYSIS.md)** - подробное сравнение различных сервисов и методов транскрибации (OpenAI Whisper API, Yandex SpeechKit, локальные решения и др.)
- **[Инструкция по настройке Yandex SpeechKit](SPEECHKIT_SETUP.md)** - пошаговая инструкция по настройке Yandex SpeechKit для транскрибации голосовых сообщений

