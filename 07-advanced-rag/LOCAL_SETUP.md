# 🚀 Быстрая настройка для локального запуска (параметры из эксперимента)

## ✅ Что уже готово

- ✅ Ollama установлен и работает
- ✅ Модель `llama3.1:8b` скачана на диск D
- ✅ Настройки из эксперимента готовы к использованию

## 📝 Настройка .env файла

Создайте файл `.env` в корне проекта со следующим содержимым:

```env
# Обязательные
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=ollama

# LLM (Ollama - как в эксперименте)
OPENAI_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.1:8b
LLM_PROVIDER=openai

# Embeddings (Ollama - работает без интернета, если HuggingFace не скачивается)
EMBEDDINGS_PROVIDER=ollama
EMBEDDINGS_MODEL=nomic-embed-text

# RAGAS (Ollama - работает без интернета)
RAGAS_EMBEDDINGS_PROVIDER=ollama
RAGAS_EMBEDDING_MODEL=nomic-embed-text

# Альтернатива: HuggingFace (если интернет работает)
# EMBEDDINGS_PROVIDER=huggingface
# EMBEDDINGS_MODEL=intfloat/multilingual-e5-base
# HUGGINGFACE_DEVICE=cpu
# HUGGINGFACE_NORMALIZE_EMBEDDINGS=true
# RAGAS_EMBEDDINGS_PROVIDER=huggingface
# RAGAS_EMBEDDING_MODEL=intfloat/multilingual-e5-base
RAGAS_LLM_MODEL=llama3.1:8b

# RAG режим (hybrid - лучший результат)
RAG_MODE=hybrid
SEMANTIC_K=4
BM25_K=4
HYBRID_K=4

# Cross-encoder (как в эксперименте)
CROSSENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
CROSSENCODER_PROVIDER=huggingface

# Дополнительные
SYSTEM_ROLE=банковский ассистент
CONTEXT_TURNS=8
RETRIEVER_K=4
DATA_PATH=@data
LOG_LEVEL=INFO
SHOW_SOURCES=false
```

## 🎯 Запуск

1. **Убедитесь, что Ollama запущен:**
   ```bash
   ollama list
   ```

2. **Установите зависимости (если еще не установлены):**
   ```bash
   make install
   ```

3. **Запустите бота:**
   ```bash
   make run
   ```

## ⚠️ Первый запуск

При первом запуске HuggingFace модели будут скачиваться автоматически:
- `intfloat/multilingual-e5-base` (~500MB)
- `cross-encoder/ms-marco-MiniLM-L-6-v2` (~50MB)

Это займет несколько минут, но только один раз.

## 📊 Что вы получите

- ✅ **Те же настройки из эксперимента** (hybrid режим, 0.778 балл)
- ✅ **Полностью локально** - никаких API ключей
- ✅ **Без VPN** - все модели локальные
- ✅ **Приватность** - данные не уходят в интернет

## 💡 Если есть GPU

Для ускорения работы embeddings используйте:
```env
HUGGINGFACE_DEVICE=cuda
```

## 📖 Подробная инструкция

См. `docs/local-config-experiment.md` для детальной информации.

