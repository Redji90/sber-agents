# Сервисы для распознавания речи (Speech-to-Text)

В проекте уже реализованы:
- ✅ **Yandex SpeechKit** - хорошо работает с OGG Opus (формат Telegram)
- ✅ **OpenAI Whisper** - через OpenAI API или Ollama

## Другие популярные сервисы

### 1. Google Cloud Speech-to-Text
**Особенности:**
- Высокая точность распознавания
- Поддержка множества языков (включая русский)
- Поддержка OGG Opus
- Платный сервис (есть бесплатный tier: 60 минут/месяц)

**API:** REST API или gRPC
**Документация:** https://cloud.google.com/speech-to-text

**Пример конфигурации:**
```yaml
speech:
  provider: "google"
  api_key: "your-google-cloud-api-key"
  project_id: "your-project-id"
  language: "ru-RU"
```

---

### 2. Azure Speech Services (Microsoft)
**Особенности:**
- Хорошая точность для русского языка
- Поддержка OGG Opus
- Платный (есть бесплатный tier: 5 часов/месяц)
- Можно использовать через REST API или SDK

**API:** REST API
**Документация:** https://azure.microsoft.com/services/cognitive-services/speech-services/

**Пример конфигурации:**
```yaml
speech:
  provider: "azure"
  api_key: "your-azure-speech-key"
  region: "eastus"  # или другой регион
  language: "ru-RU"
```

---

### 3. Amazon Transcribe (AWS)
**Особенности:**
- Высокая точность
- Поддержка OGG Opus
- Платный сервис
- Требует AWS аккаунт

**API:** REST API (через boto3)
**Документация:** https://aws.amazon.com/transcribe/

**Пример конфигурации:**
```yaml
speech:
  provider: "aws"
  access_key_id: "your-access-key"
  secret_access_key: "your-secret-key"
  region: "us-east-1"
  language: "ru-RU"
```

---

### 4. Deepgram
**Особенности:**
- Быстрое распознавание (низкая задержка)
- Хорошая точность
- Поддержка OGG Opus
- Платный (есть бесплатный tier: 12,000 минут/месяц)

**API:** REST API или WebSocket
**Документация:** https://deepgram.com/

**Пример конфигурации:**
```yaml
speech:
  provider: "deepgram"
  api_key: "your-deepgram-api-key"
  language: "ru"
```

---

### 5. AssemblyAI
**Особенности:**
- Хорошая точность
- Поддержка OGG Opus
- Платный (есть бесплатный tier: 5 часов/месяц)
- Простой REST API

**API:** REST API
**Документация:** https://www.assemblyai.com/

**Пример конфигурации:**
```yaml
speech:
  provider: "assemblyai"
  api_key: "your-assemblyai-api-key"
  language: "ru"
```

---

### 6. Rev.ai
**Особенности:**
- Высокая точность
- Поддержка OGG Opus
- Платный сервис
- Быстрое распознавание

**API:** REST API
**Документация:** https://www.rev.ai/

**Пример конфигурации:**
```yaml
speech:
  provider: "rev"
  api_key: "your-rev-api-key"
  language: "ru"
```

---

### 7. Speechmatics
**Особенности:**
- Высокая точность
- Поддержка OGG Opus
- Платный сервис
- Хорошая поддержка русского языка

**API:** REST API
**Документация:** https://www.speechmatics.com/

**Пример конфигурации:**
```yaml
speech:
  provider: "speechmatics"
  api_key: "your-speechmatics-api-key"
  language: "ru"
```

---

## Локальные (офлайн) решения

### 8. Vosk
**Особенности:**
- ✅ Бесплатный и открытый исходный код
- ✅ Работает офлайн (не требует интернет)
- ✅ Поддержка русского языка
- ⚠️ Требует установки модели (размер ~1-2 ГБ)
- ⚠️ Может быть медленнее облачных решений

**Установка:**
```bash
pip install vosk
# Скачать модель: https://alphacephei.com/vosk/models
```

**Пример конфигурации:**
```yaml
speech:
  provider: "vosk"
  model_path: "path/to/vosk-model-ru"
  language: "ru"
```

---

### 9. Mozilla DeepSpeech
**Особенности:**
- ✅ Бесплатный и открытый исходный код
- ✅ Работает офлайн
- ⚠️ Ограниченная поддержка русского языка
- ⚠️ Требует установки модели

**Установка:**
```bash
pip install deepspeech
# Скачать модель: https://github.com/mozilla/DeepSpeech/releases
```

---

### 10. Coqui STT (ранее Mozilla TTS)
**Особенности:**
- ✅ Бесплатный и открытый исходный код
- ✅ Работает офлайн
- ✅ Хорошая поддержка русского языка
- ⚠️ Требует установки модели

**Установка:**
```bash
pip install coqui-stt
# Скачать модель: https://coqui.ai/models
```

---

## Сравнение сервисов

| Сервис | Точность | Скорость | Стоимость | OGG Opus | Русский язык |
|--------|----------|----------|-----------|----------|--------------|
| Yandex SpeechKit | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Платный | ✅ | ✅ Отлично |
| OpenAI Whisper | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | Платный | ✅ | ✅ Отлично |
| Google Cloud STT | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Платный | ✅ | ✅ Отлично |
| Azure Speech | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Платный | ✅ | ✅ Отлично |
| Deepgram | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Платный | ✅ | ✅ Хорошо |
| AssemblyAI | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Платный | ✅ | ✅ Хорошо |
| Vosk | ⭐⭐⭐ | ⭐⭐⭐ | Бесплатно | ✅ | ✅ Хорошо |
| DeepSpeech | ⭐⭐⭐ | ⭐⭐⭐ | Бесплатно | ⚠️ | ⚠️ Ограничено |

## Рекомендации

### Для продакшена:
1. **Yandex SpeechKit** - лучший выбор для русского языка, хорошо работает с OGG Opus
2. **Google Cloud STT** - высокая точность, хорошая поддержка русского
3. **Azure Speech** - хорошая альтернатива, стабильная работа

### Для разработки/тестирования:
1. **Vosk** - бесплатно, работает офлайн, не требует API ключей
2. **OpenAI Whisper** - если уже используете OpenAI API

### Для максимальной скорости:
1. **Deepgram** - самый быстрый из облачных решений
2. **AssemblyAI** - хороший баланс скорости и точности

## Добавление нового провайдера

Чтобы добавить новый провайдер в проект:

1. Добавьте функцию `transcribe_<provider>` в `bot/main.py`
2. Добавьте обработку в функцию `transcribe_audio()`
3. Обновите `bot/config.py` для поддержки новых параметров конфигурации
4. Обновите `config.yaml` с примером конфигурации

Пример структуры функции:
```python
async def transcribe_<provider>(audio_path: str) -> str:
    """Transcribe audio using <Provider Name>."""
    # Реализация API вызова
    # Обработка ошибок
    # Возврат текста
    pass
```

