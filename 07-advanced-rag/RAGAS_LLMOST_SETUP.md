# Быстрая настройка LLMost для RAGAS Evaluation

## Проблема
Groq имеет строгие rate limits (6000 TPM), из-за чего метрики RAGAS (`faithfulness`, `answer_correctness`, `context_recall`, `context_precision`) возвращают `nan` и конвертируются в 0.0.

## Решение
Использовать LLMost для RAGAS evaluation, оставив Groq для основного бота.

## Шаги настройки

### 1. Получите API ключ LLMost

1. Зарегистрируйтесь на **https://llmost.ru/**
2. Перейдите в раздел API Keys в личном кабинете
3. Создайте новый API ключ
4. **Сохраните ключ** (он показывается только один раз!)

### 2. Обновите `.env` файл

Добавьте следующие строки в ваш `.env` файл:

```env
# Основной бот - Groq (оставляем как есть)
OPENAI_BASE_URL=https://api.groq.com/openai/v1
LLM_MODEL=openai/gpt-oss-20b
OPENAI_API_KEY=your_groq_api_key_here

# RAGAS evaluation - LLMost (чтобы не бить лимиты Groq)
RAGAS_LLM_MODEL=x-ai/grok-4.1-fast
RAGAS_OPENAI_BASE_URL=https://llmost.ru/api/v1
RAGAS_OPENAI_API_KEY=your_llmost_api_key_here
```

**Важно:**
- Замените `your_llmost_api_key_here` на ваш реальный API ключ от LLMost
- **Правильный URL для LLMost: `https://llmost.ru/api/v1`** (проверено и работает!)

### 3. Перезапустите бота

После обновления `.env` файла перезапустите бота, чтобы применить изменения.

### 4. Проверьте работу

Запустите `/evaluate_dataset` в боте. Теперь все метрики должны вычисляться корректно!

## Альтернативные модели LLMost

Если `x-ai/grok-4.1-fast` не работает, попробуйте другие модели:
- `gpt-4`
- `gpt-4-turbo`
- Проверьте список доступных моделей на https://llmost.ru/docs

## Проверка подключения

Для проверки подключения к LLMost можно использовать скрипт:

```bash
uv run python scripts/test_llmost.py
```

Этот скрипт проверит:
- Подключение к LLMost API (пробует оба варианта URL)
- Доступность модели
- Корректность API ключа

## Альтернатива: Ollama для RAGAS (если LLMost недоступен)

Если LLMost недоступен или возникают проблемы с подключением, можно использовать Ollama локально:

### Настройка Ollama для RAGAS

1. **Убедитесь, что Ollama запущен:**
   ```bash
   ollama serve
   ```

2. **Установите модель (если еще не установлена):**
   ```bash
   ollama pull llama3.1:8b
   ```

3. **Обновите `.env` файл:**
   ```env
   # RAGAS evaluation - Ollama (локально)
   RAGAS_LLM_MODEL=llama3.1:8b
   RAGAS_OPENAI_BASE_URL=http://localhost:11434/v1
   RAGAS_OPENAI_API_KEY=ollama  # Любое значение, Ollama не требует ключа
   ```

4. **Перезапустите бота и запустите `/evaluate_dataset`**

**Преимущества Ollama:**
- ✅ Работает полностью локально (без интернета)
- ✅ Нет rate limits
- ✅ Бесплатно
- ✅ Все метрики вычисляются стабильно

**Недостатки:**
- ⚠️ Требует локального запуска Ollama
- ⚠️ Может быть медленнее, чем облачные API

