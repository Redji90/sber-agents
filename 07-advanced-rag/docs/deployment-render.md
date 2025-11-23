# Деплой бота на Render.com для работы с Groq

Эта инструкция поможет вам развернуть Telegram-бота на Render.com, чтобы он работал с Groq API без необходимости VPN.

## Преимущества Render.com

- ✅ **Бесплатный tier** для веб-сервисов
- ✅ **Автоматический деплой** из Git репозитория
- ✅ **Доступ к Groq API** без VPN (серверы в США/Европе)
- ✅ **Автоматические перезапуски** при сбоях
- ✅ **Логи в реальном времени**

## Предварительные требования

1. Аккаунт на [Render.com](https://render.com) (бесплатный)
2. Аккаунт на [Groq.com](https://console.groq.com) (бесплатный)
3. API ключ от Groq (получить можно в [консоли Groq](https://console.groq.com/keys))
4. Telegram Bot Token (получить от [@BotFather](https://t.me/BotFather))
5. Git репозиторий (GitHub, GitLab или Bitbucket)

## Шаг 1: Подготовка Groq API ключа

1. Зарегистрируйтесь на [console.groq.com](https://console.groq.com)
2. Перейдите в раздел [API Keys](https://console.groq.com/keys)
3. Создайте новый API ключ
4. Скопируйте ключ (он понадобится на шаге 3)

**Примечание:** Groq бесплатный, но имеет лимит 6000 токенов в минуту (TPM). Для бота этого достаточно.

## Шаг 2: Подготовка Telegram Bot Token

1. Откройте [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте токен (он понадобится на шаге 3)

## Шаг 3: Деплой на Render.com

### Вариант A: Через Render Dashboard (рекомендуется)

1. **Войдите в Render.com**
   - Зарегистрируйтесь на [render.com](https://render.com)
   - Подключите ваш Git репозиторий (GitHub/GitLab/Bitbucket)

2. **Создайте новый Web Service**
   - Нажмите "New +" → "Web Service"
   - Выберите ваш репозиторий и ветку (обычно `main`)
   - Render автоматически определит Dockerfile
   
   **Примечание:** Код бота автоматически запускает простой HTTP сервер для health check, поэтому Web Service будет работать корректно.

3. **Настройте сервис**
   - **Name:** `telegram-bot` (или любое другое имя)
   - **Region:** Выберите ближайший регион (например, `Oregon (US West)`)
   - **Branch:** `main` (или ваша рабочая ветка)
   - **Root Directory:** оставьте пустым (если проект в корне)
   - **⚠️ ВАЖНО: Environment:** Найдите выпадающий список "Environment" (обычно выше полей Build/Start Command) и выберите **`Docker`** (не Python!)
   - **Dockerfile Path:** `Dockerfile` (если в корне проекта)
   
   **Примечание:** Если вы видите поля "Build Command" и "Start Command" с `pip install` и `gunicorn`, значит выбрана среда "Python". Прокрутите страницу вверх и найдите поле "Environment", выберите "Docker". После выбора Docker поля Build/Start Command исчезнут, так как всё будет определяться из Dockerfile.

4. **Настройте переменные окружения**
   В разделе "Environment Variables" добавьте:

   ```env
   # Обязательные переменные
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
   OPENAI_API_KEY=your_groq_api_key_here
   
   # Настройки для Groq
   OPENAI_BASE_URL=https://api.groq.com/openai/v1
   LLM_MODEL=llama-3.1-8b-instant
   LLM_PROVIDER=openai
   
   # Настройки эмбеддингов (HuggingFace - бесплатно)
   EMBEDDINGS_PROVIDER=huggingface
   EMBEDDINGS_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
   RAGAS_EMBEDDINGS_PROVIDER=huggingface
   RAGAS_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
   HUGGINGFACE_DEVICE=cpu
   HUGGINGFACE_NORMALIZE_EMBEDDINGS=true
   
   # Дополнительные настройки
   SYSTEM_ROLE=банковский ассистент
   CONTEXT_TURNS=8
   RETRIEVER_K=4
   DATA_PATH=@data
   LOG_LEVEL=INFO
   SHOW_SOURCES=false
   ```

   **Важно:** Замените `your_telegram_bot_token_here` и `your_groq_api_key_here` на реальные значения!

5. **Настройте ресурсы (для бесплатного tier)**
   - **Instance Type:** `Free` (512 MB RAM, 0.5 CPU)
   - Этого достаточно для работы бота

6. **Запустите деплой**
   - Нажмите "Create Web Service"
   - Render начнет сборку Docker образа и деплой
   - Процесс займет 5-10 минут

### Вариант B: Через render.yaml (автоматический)

Если вы используете файл `render.yaml` из репозитория:

1. Создайте новый Web Service в Render Dashboard
2. Выберите "Apply render.yaml"
3. Render автоматически подхватит настройки из `render.yaml`
4. **Важно:** Вам все равно нужно будет вручную добавить секретные переменные:
   - `TELEGRAM_BOT_TOKEN`
   - `OPENAI_API_KEY` (ваш Groq API ключ)

## Шаг 4: Проверка работы

1. **Проверьте логи**
   - В Render Dashboard откройте раздел "Logs"
   - Должны увидеть: `Запуск Telegram-бота...`
   - Если есть ошибки, проверьте переменные окружения

2. **Протестируйте бота**
   - Откройте вашего бота в Telegram
   - Отправьте команду `/start`
   - Бот должен ответить

3. **Проверьте работу с Groq**
   - Отправьте боту любой вопрос
   - Бот должен ответить (используя Groq API)
   - Проверьте логи в Render - не должно быть ошибок подключения

## Решение проблем

### Бот не отвечает

1. **Проверьте логи в Render Dashboard**
   - Ищите ошибки подключения к Telegram API
   - Проверьте, что `TELEGRAM_BOT_TOKEN` установлен правильно

2. **Проверьте переменные окружения**
   - Убедитесь, что все обязательные переменные установлены
   - Проверьте, что нет опечаток в значениях

### Ошибки подключения к Groq

1. **Проверьте API ключ**
   - Убедитесь, что `OPENAI_API_KEY` содержит ваш Groq API ключ
   - Проверьте, что ключ активен в консоли Groq

2. **Проверьте base_url**
   - Должно быть: `OPENAI_BASE_URL=https://api.groq.com/openai/v1`
   - Должно быть: `LLM_MODEL=llama-3.1-8b-instant` (или другая модель Groq)

### Ошибки с эмбеддингами

Если возникают проблемы с HuggingFace моделями:

1. **Увеличьте память** (если возможно)
   - В Render Dashboard → Settings → Plan
   - Перейдите на Starter ($7/месяц) для больше памяти

2. **Используйте более легкую модель**
   ```env
   EMBEDDINGS_MODEL=cointegrated/rubert-tiny2
   RAGAS_EMBEDDING_MODEL=cointegrated/rubert-tiny2
   ```

### Rate limiting от Groq

Groq имеет лимит 6000 TPM. Если получаете ошибки 429:

1. **Увеличьте задержку между запросами** (если используете evaluation):
   ```env
   EVALUATION_DELAY_BETWEEN_REQUESTS=3.0
   ```

2. **Уменьшите параллелизм**:
   ```env
   EVALUATION_MAX_CONCURRENT=1
   ```

## Обновление бота

Render автоматически обновляет бота при пуше в Git:

1. Сделайте изменения в коде
2. Закоммитьте и запушьте в репозиторий
3. Render автоматически запустит новый деплой
4. Проверьте логи, чтобы убедиться, что деплой успешен

## Мониторинг

- **Логи:** Render Dashboard → Logs (в реальном времени)
- **Метрики:** Render Dashboard → Metrics (CPU, память, сеть)
- **События:** Render Dashboard → Events (деплои, перезапуски)

## Альтернативные платформы

Если Render.com не подходит, можно использовать:

- **Railway.app** - похожий сервис, бесплатный tier
- **Fly.io** - бесплатный tier, хорошая производительность
- **Heroku** - больше не бесплатный, но есть альтернативы

Инструкции для других платформ можно найти в интернете.

## Стоимость

- **Render Free Tier:** Бесплатно
  - 512 MB RAM
  - 0.5 CPU
  - Автоматическое засыпание после 15 минут бездействия
  - Просыпается при первом запросе (занимает ~30 секунд)

- **Render Starter:** $7/месяц (опционально)
  - 512 MB RAM
  - 0.5 CPU
  - Без засыпания
  - Лучше для продакшена

**Groq API:** Бесплатно (лимит 6000 TPM)

## Дополнительные настройки

### Индексация документов

После деплоя нужно проиндексировать документы:

1. Откройте бота в Telegram
2. Отправьте команду `/index`
3. Дождитесь завершения индексации

### LangSmith трейсинг (опционально)

Если хотите отслеживать запросы через LangSmith:

1. Получите API ключ на [smith.langchain.com](https://smith.langchain.com)
2. Добавьте в переменные окружения Render:
   ```env
   LANGSMITH_API_KEY=lsv2_pt_your_key_here
   LANGSMITH_PROJECT=telegram-bot
   ```

## Поддержка

Если возникли проблемы:
1. Проверьте логи в Render Dashboard
2. Проверьте документацию Render: [render.com/docs](https://render.com/docs)
3. Проверьте документацию Groq: [console.groq.com/docs](https://console.groq.com/docs)

