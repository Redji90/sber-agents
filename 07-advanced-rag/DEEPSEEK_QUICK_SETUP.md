# 🚀 Быстрая настройка DeepSeek

## Вариант 1: Через OpenGate (рекомендуется, проще всего)

### Шаг 1: Получите OpenGate API ключ

1. Откройте https://opengatellm.ru/ или https://opengate.ink/
2. Получите API ключ (см. `docs/opengate-api-key-quick.md`)

### Шаг 2: Обновите `.env` файл

Добавьте или измените следующие строки:

```env
# LLM (DeepSeek через OpenGate)
LLM_PROVIDER=openai
OPENAI_BASE_URL=https://api.opengatellm.ru/v1
LLM_MODEL=deepseek-chat
OPENAI_API_KEY=your_opengate_api_key_here

# RAGAS LLM (можно использовать ту же модель)
RAGAS_LLM_MODEL=deepseek-chat
```

**Важно:** Проверьте точное название модели в каталоге OpenGate: https://opengatellm.ru/catalog.html

Модель может называться:
- `deepseek-chat`
- `deepseek/deepseek-chat`
- `deepseek-coder` (для кода)

### Шаг 3: Запустите бота

```bash
make run
```

---

## Вариант 2: Через официальный DeepSeek API

### Шаг 1: Получите DeepSeek API ключ

1. Зарегистрируйтесь на https://www.deepseek.ru/
2. Получите API ключ в личном кабинете

### Шаг 2: Обновите `.env` файл

```env
# LLM (DeepSeek официальный API)
LLM_PROVIDER=openai
OPENAI_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
OPENAI_API_KEY=your_deepseek_api_key_here

# RAGAS LLM
RAGAS_LLM_MODEL=deepseek-chat
```

**Примечание:** Проверьте актуальный endpoint и название модели в документации DeepSeek.

### Шаг 3: Запустите бота

```bash
make run
```

---

## 📝 Полный пример `.env` для DeepSeek

```env
# Обязательные
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_opengate_or_deepseek_key_here

# LLM (DeepSeek)
LLM_PROVIDER=openai
OPENAI_BASE_URL=https://api.opengatellm.ru/v1
LLM_MODEL=deepseek-chat
RAGAS_LLM_MODEL=deepseek-chat

# Embeddings (можно оставить как есть)
EMBEDDINGS_PROVIDER=ollama
EMBEDDINGS_MODEL=nomic-embed-text

# RAG режим
RAG_MODE=hybrid
SEMANTIC_K=4
BM25_K=4
HYBRID_K=4

# Дополнительные
SYSTEM_ROLE=банковский ассистент
CONTEXT_TURNS=8
RETRIEVER_K=4
DATA_PATH=@data
LOG_LEVEL=INFO
SHOW_SOURCES=false
```

---

## ⚠️ Важно

1. **Проверьте название модели:**
   - Откройте каталог OpenGate: https://opengatellm.ru/catalog.html
   - Найдите DeepSeek в списке
   - Используйте точное название модели

2. **Если модель не работает:**
   - Проверьте, что API ключ правильный
   - Убедитесь, что модель доступна в OpenGate
   - Попробуйте альтернативное название: `deepseek/deepseek-chat`

---

## 🎯 Рекомендация

**Используйте OpenGate** - это самый простой способ, не требует отдельной регистрации на DeepSeek (если у вас уже есть OpenGate ключ).

Подробная инструкция: `docs/deepseek-setup.md`


