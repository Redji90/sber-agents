# Настройка российских LLM API

## Доступные варианты для России

### 1. Yandex GPT (рекомендуется)

**Преимущества:**
- Работает в России без VPN
- Оптимизирована для русского языка
- Есть бесплатный tier
- OpenAI-совместимый API (частично)

**Регистрация:**
1. Перейдите на https://yandex.cloud/
2. Создайте аккаунт или войдите
3. Создайте каталог (folder)
4. Перейдите в раздел "Foundation Models"
5. Получите API ключ

**Настройка в `.env`:**
```env
OPENAI_BASE_URL=https://llm.api.cloud.yandex.net/foundationModels/v1/completion
LLM_MODEL=yandexgpt
OPENAI_API_KEY=your_yandex_api_key_here
RAGAS_LLM_MODEL=yandexgpt
```

**Примечание:** Yandex GPT может использовать другой формат API. Если стандартный OpenAI client не работает, может потребоваться кастомная интеграция.

### 2. GigaChat (от Сбера)

**Преимущества:**
- Работает в России без VPN
- Оптимизирована для русского языка
- Есть бесплатный tier
- Хорошее качество для русского языка

**Регистрация:**
1. Перейдите на https://developers.sber.ru/gigachat
2. Создайте аккаунт через Sber ID
3. Получите API ключ в разделе "GigaChat"

**Настройка в `.env`:**
```env
OPENAI_BASE_URL=https://gigachat.devices.sberbank.ru/api/v1
LLM_MODEL=GigaChat
OPENAI_API_KEY=your_gigachat_api_key_here
RAGAS_LLM_MODEL=GigaChat
```

**Примечание:** GigaChat использует свой формат API, не совместимый с OpenAI. Может потребоваться кастомная интеграция.

### 3. LLMost (OpenAI-совместимый)

**Преимущества:**
- Работает в России без VPN
- OpenAI-совместимый API (легкая интеграция)
- Есть бесплатный tier
- Доступ к различным моделям

**Регистрация:**
1. Перейдите на https://llmost.ru/
2. Зарегистрируйтесь
3. Получите API ключ

**Настройка в `.env`:**
```env
OPENAI_BASE_URL=https://api.llmost.ru/v1
LLM_MODEL=gpt-3.5-turbo
OPENAI_API_KEY=your_llmost_api_key_here
RAGAS_LLM_MODEL=gpt-3.5-turbo
```

### 4. OpenGate (OpenAI-совместимый)

**Преимущества:**
- Работает в России без VPN
- OpenAI-совместимый API
- Доступ к различным моделям (Gemini, Grok, DeepSeek, Qwen, Mistral, Llama)

**Регистрация:**
1. Перейдите на https://opengatellm.ru/
2. Зарегистрируйтесь
3. Получите API ключ

**Настройка в `.env`:**
```env
OPENAI_BASE_URL=https://api.opengatellm.ru/v1
LLM_MODEL=llama-3.1-8b-instruct
OPENAI_API_KEY=your_opengate_api_key_here
RAGAS_LLM_MODEL=llama-3.1-8b-instruct
```

## Рекомендации

1. **Для быстрого старта**: Используйте **LLMost** или **OpenGate** - они имеют OpenAI-совместимый API и легко интегрируются.

2. **Для лучшего качества на русском**: Используйте **Yandex GPT** или **GigaChat** - они оптимизированы для русского языка.

3. **Для локального использования**: Используйте **Ollama** - полностью бесплатно и работает локально.

## Проверка работы

После настройки проверьте работу LLM:

```bash
uv run python scripts/test_llm.py
```

Если тест проходит успешно, можно запускать evaluation:

```bash
make reindex-and-evaluate
```

## Известные проблемы

1. **Yandex GPT и GigaChat**: Могут использовать нестандартный формат API. Если стандартный OpenAI client не работает, может потребоваться кастомная интеграция через `langchain-community` или прямое использование их SDK.

2. **LLMost и OpenGate**: Должны работать с стандартным OpenAI client, так как они OpenAI-совместимые.

## Альтернатива: Ollama (локально)

Если API не работают, можно использовать Ollama локально:

```env
OPENAI_BASE_URL=http://localhost:11434/v1
LLM_MODEL=llama3.1:8b
OPENAI_API_KEY=ollama
```

Установка Ollama: https://ollama.ai/


