# Настройка бота на Render без VPN (на основе лучших результатов эксперимента)

## 🎯 Цель

Использовать настройки из эксперимента, которые показали лучший результат (hybrid режим, 0.778 средний балл), но адаптированные для работы на Render.com без VPN.

## 📊 Исходные настройки из эксперимента

- **Режим:** hybrid (лучший результат)
- **LLM:** llama3.1:8b (Ollama) ❌ - не работает на Render
- **Embeddings:** intfloat/multilingual-e5-base (HuggingFace) ✅ - работает
- **RAGAS LLM:** llama3.1:8b (Ollama) ❌ - не работает на Render
- **RAGAS Embeddings:** intfloat/multilingual-e5-base (HuggingFace) ✅ - работает
- **Cross-encoder:** cross-encoder/mmarco-mMiniLMv2-L12-H384-v1 (HuggingFace) ✅ - работает

## ✅ Адаптированные настройки для Render

### Что работает без VPN на Render:

1. **HuggingFace модели** - работают без VPN, скачиваются при первом запуске
2. **Groq API** - работает на серверах Render без VPN (серверы в США/Европе)

### Что НЕ работает на Render:

1. **Ollama** - требует локальный сервер, не работает на Render Free tier

## 🔧 Настройка для Render

### Переменные окружения в Render Dashboard:

```env
# Обязательные
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
OPENAI_API_KEY=your_groq_api_key_here

# LLM настройки (Groq вместо Ollama)
OPENAI_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=llama-3.1-8b-instant
LLM_PROVIDER=openai

# Embeddings (HuggingFace - как в эксперименте)
EMBEDDINGS_PROVIDER=huggingface
EMBEDDINGS_MODEL=intfloat/multilingual-e5-base
HUGGINGFACE_DEVICE=cpu
HUGGINGFACE_NORMALIZE_EMBEDDINGS=true

# RAGAS настройки (HuggingFace для embeddings, Groq для LLM)
RAGAS_EMBEDDINGS_PROVIDER=huggingface
RAGAS_EMBEDDING_MODEL=intfloat/multilingual-e5-base
RAGAS_LLM_MODEL=llama-3.1-8b-instant

# RAG режим (hybrid - лучший результат)
RAG_MODE=hybrid
SEMANTIC_K=4
BM25_K=4
HYBRID_K=4

# Cross-encoder для reranking (если используете hybrid+reranker)
CROSSENCODER_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
CROSSENCODER_PROVIDER=huggingface

# Дополнительные настройки
SYSTEM_ROLE=банковский ассистент
CONTEXT_TURNS=8
RETRIEVER_K=4
DATA_PATH=@data
LOG_LEVEL=INFO
SHOW_SOURCES=false
```

## 📝 Пошаговая инструкция

### 1. Получите Groq API ключ

1. Зарегистрируйтесь на [console.groq.com](https://console.groq.com)
2. Перейдите в [API Keys](https://console.groq.com/keys)
3. Создайте новый ключ
4. Скопируйте ключ

### 2. Настройте переменные окружения в Render

1. Откройте Render Dashboard → ваш сервис → Environment
2. Добавьте все переменные из списка выше
3. Замените `your_telegram_bot_token_here` и `your_groq_api_key_here` на реальные значения

### 3. Дождитесь деплоя

Render автоматически:
- Скачает HuggingFace модели при первом запуске
- Настроит все компоненты
- Запустит бота

## 🎯 Отличия от эксперимента

| Компонент | Эксперимент | Render |
|-----------|-------------|--------|
| LLM | Ollama (llama3.1:8b) | Groq (llama-3.1-8b-instant) |
| Embeddings | HuggingFace (intfloat/multilingual-e5-base) | HuggingFace (intfloat/multilingual-e5-base) ✅ |
| RAGAS LLM | Ollama (llama3.1:8b) | Groq (llama-3.1-8b-instant) |
| RAGAS Embeddings | HuggingFace (intfloat/multilingual-e5-base) | HuggingFace (intfloat/multilingual-e5-base) ✅ |
| Cross-encoder | HuggingFace | HuggingFace ✅ |
| Режим RAG | hybrid | hybrid ✅ |

## ⚠️ Важные замечания

1. **Первый запуск может быть медленным** - HuggingFace модели скачиваются при первом запуске (1-2 минуты)

2. **Память на Render Free tier** - модель `intfloat/multilingual-e5-base` требует ~500MB RAM. На Free tier (512MB) может быть тесно. Если возникнут проблемы:
   - Используйте более легкую модель: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
   - Или перейдите на Starter plan ($7/месяц, 512MB RAM, но без засыпания)

3. **Groq vs Ollama** - Groq использует ту же модель (llama-3.1-8b), но через API. Качество должно быть сопоставимым.

4. **Cross-encoder** - если используете `hybrid+reranker`, модель `cross-encoder/ms-marco-MiniLM-L-6-v2` также скачается при первом запуске.

## 🚀 Проверка работы

После деплоя:

1. Откройте бота в Telegram
2. Отправьте `/start`
3. Отправьте `/index` для индексации документов
4. Проверьте логи в Render Dashboard → Logs
   - Должно быть: `Запуск Telegram-бота...`
   - Должно быть: `Используется HuggingFace embeddings: intfloat/multilingual-e5-base`
   - Не должно быть ошибок

## 💡 Альтернатива: более легкая модель

Если на Free tier не хватает памяти для `intfloat/multilingual-e5-base`, используйте:

```env
EMBEDDINGS_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
RAGAS_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
```

Эта модель легче (~200MB), но качество может быть немного ниже.

## 📊 Ожидаемые результаты

С этими настройками вы должны получить:
- **Режим:** hybrid (как в эксперименте)
- **Embeddings:** те же модели HuggingFace (без VPN)
- **LLM:** Groq (быстро, бесплатно, без VPN на Render)
- **Качество:** должно быть близко к результатам эксперимента

## ❓ Вопросы?

Если возникнут проблемы:
1. Проверьте логи в Render Dashboard → Logs
2. Убедитесь, что все переменные окружения установлены
3. Проверьте, что HuggingFace модели скачались (первые строки логов)


