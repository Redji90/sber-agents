# Быстрый старт: Деплой бота на Render.com с Groq

Эта инструкция поможет вам быстро развернуть Telegram-бота на Render.com для работы с Groq API без VPN.

## Что вам понадобится

1. ✅ Аккаунт на [Render.com](https://render.com) (бесплатный)
2. ✅ API ключ от [Groq.com](https://console.groq.com/keys) (бесплатный)
3. ✅ Telegram Bot Token от [@BotFather](https://t.me/BotFather)
4. ✅ Git репозиторий (GitHub/GitLab/Bitbucket)

## Шаги деплоя (5 минут)

### 1. Получите API ключи

**Groq API ключ:**
- Зарегистрируйтесь на [console.groq.com](https://console.groq.com)
- Перейдите в [API Keys](https://console.groq.com/keys)
- Создайте новый ключ и скопируйте его

**Telegram Bot Token:**
- Откройте [@BotFather](https://t.me/BotFather) в Telegram
- Отправьте `/newbot` и следуйте инструкциям
- Скопируйте токен

### 2. Деплой на Render

1. **Войдите в Render.com** и подключите ваш Git репозиторий

2. **Создайте Web Service:**
   - Нажмите "New +" → "Web Service"
   - Выберите репозиторий и ветку `main`
   - Render автоматически определит Dockerfile

3. **Настройте переменные окружения:**
   
   В разделе "Environment Variables" добавьте:

   ```env
   TELEGRAM_BOT_TOKEN=ваш_telegram_токен
   OPENAI_API_KEY=ваш_groq_api_ключ
   OPENAI_BASE_URL=https://api.groq.com/openai/v1
   LLM_MODEL=llama-3.1-8b-instant
   LLM_PROVIDER=openai
   EMBEDDINGS_PROVIDER=huggingface
   EMBEDDINGS_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
   RAGAS_EMBEDDINGS_PROVIDER=huggingface
   RAGAS_EMBEDDING_MODEL=sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2
   HUGGINGFACE_DEVICE=cpu
   HUGGINGFACE_NORMALIZE_EMBEDDINGS=true
   SYSTEM_ROLE=банковский ассистент
   CONTEXT_TURNS=8
   RETRIEVER_K=4
   DATA_PATH=@data
   LOG_LEVEL=INFO
   SHOW_SOURCES=false
   ```

4. **Выберите Free Plan** и нажмите "Create Web Service"

5. **Дождитесь деплоя** (5-10 минут)

### 3. Проверьте работу

1. Откройте бота в Telegram
2. Отправьте `/start`
3. Бот должен ответить!

### 4. Проиндексируйте документы

После первого запуска нужно проиндексировать документы:

1. Откройте бота в Telegram
2. Отправьте команду `/index`
3. Дождитесь завершения индексации

## Готово! 🎉

Теперь ваш бот работает на Render.com и использует Groq API без VPN!

## Что дальше?

- **Логи:** Render Dashboard → Logs (просмотр в реальном времени)
- **Обновления:** Просто пушите изменения в Git - Render автоматически обновит бота
- **Мониторинг:** Render Dashboard → Metrics (CPU, память, сеть)

## Проблемы?

См. подробную инструкцию: [docs/deployment-render.md](docs/deployment-render.md)

## Стоимость

- **Render Free Tier:** Бесплатно (512 MB RAM, автозасыпание после 15 мин)
- **Groq API:** Бесплатно (лимит 6000 TPM)

**Итого: 0₽/месяц** 🎉

