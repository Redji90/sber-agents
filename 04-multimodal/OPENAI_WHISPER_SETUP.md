# Настройка OpenAI Whisper API для транскрибации

## Варианты использования

### Вариант 1: Через Ollama (рекомендуется, если у вас уже настроен Ollama)

Если у вас уже запущен Ollama с поддержкой Whisper:

1. Убедитесь, что Ollama запущен и доступен
2. В `config.yaml` должно быть:
   ```yaml
   speech:
     provider: "openai"
     api_key: ""  # не требуется для Ollama
     base_url: ""  # будет использован из llm секции
     language: "ru"  # или "auto" для автоматического определения
   ```

3. Ollama автоматически использует настройки из секции `llm`:
   ```yaml
   llm:
     base_url: "http://195.209.210.171:11434/v1/"
   ```

**Примечание:** Ollama должен поддерживать Whisper API. Если Whisper не работает через Ollama, используйте вариант 2.

### Вариант 2: Через OpenAI API напрямую

Если хотите использовать официальный OpenAI API:

1. Получите API-ключ OpenAI на https://platform.openai.com/api-keys
2. В `config.yaml` укажите:
   ```yaml
   speech:
     provider: "openai"
     api_key: "sk-your-openai-api-key-here"
     base_url: ""  # или "https://api.openai.com/v1" (по умолчанию)
     language: "ru"
   ```

**Стоимость:** $0.006 за минуту аудио (~$0.36 за час)

### Вариант 3: Через другой OpenAI-совместимый API

Если у вас есть доступ к другому OpenAI-совместимому API:

```yaml
speech:
  provider: "openai"
  api_key: "your-api-key"
  base_url: "https://your-api-endpoint.com/v1"
  language: "ru"
```

## Текущая конфигурация

В вашем проекте уже настроено:
- Provider: `openai`
- Использует Ollama по адресу: `http://195.209.210.171:11434/v1/`
- Язык: `ru` (русский)

## Проверка работы

1. Запустите бота:
   ```bash
   uv run python -m bot.main
   ```

2. Отправьте голосовое сообщение боту

3. Если появляется ошибка, проверьте логи:
   - Убедитесь, что Ollama запущен и доступен
   - Проверьте, что Ollama поддерживает Whisper API
   - Если нет - используйте OpenAI API напрямую (вариант 2)

## Поддержка языков

Язык указывается в формате ISO 639-1:
- `ru` - русский
- `en` - английский
- `auto` - автоматическое определение (по умолчанию, если не указано)

## Устранение проблем

### Ошибка: "Model not found" или "Whisper not available"

**Решение:** Ollama не поддерживает Whisper API. Используйте OpenAI API напрямую (вариант 2).

### Ошибка: "Connection refused" или "Cannot connect to Ollama"

**Решение:** 
1. Убедитесь, что Ollama запущен на `http://195.209.210.171:11434`
2. Проверьте доступность сервера
3. Проверьте настройки `base_url` в `config.yaml`

### Ошибка: "Invalid API key" (при использовании OpenAI API)

**Решение:**
1. Проверьте правильность API-ключа
2. Убедитесь, что у вас есть доступ к OpenAI API
3. Проверьте баланс на аккаунте OpenAI

