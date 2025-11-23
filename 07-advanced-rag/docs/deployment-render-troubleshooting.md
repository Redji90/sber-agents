# Решение проблем при деплое на Render.com

## Проблема: Вижу поля Build Command и Start Command вместо Docker

### Симптомы
На странице создания Web Service вы видите:
- **Build Command:** `$ pip install -r requirements.txt`
- **Start Command:** `$ gunicorn your_application.wsgi` (с красной рамкой)

### Причина
Выбрана среда "Python" вместо "Docker".

### Решение

1. **Прокрутите страницу вверх** и найдите поле **"Environment"** (обычно в начале формы, после выбора репозитория)

2. **Измените значение** с "Python" на **"Docker"**

3. После выбора Docker:
   - Поля "Build Command" и "Start Command" **исчезнут** (это нормально!)
   - Появится поле **"Dockerfile Path"** (если его нет, оставьте пустым или укажите `Dockerfile`)
   - Render будет использовать ваш Dockerfile для сборки и запуска

4. **Продолжите настройку:**
   - Укажите имя сервиса
   - Выберите регион
   - Добавьте переменные окружения
   - Нажмите "Create Web Service"

## Альтернатива: Если Docker не доступен

Если по какой-то причине вы не можете использовать Docker, можно использовать стандартные команды Python:

### Build Command:
```bash
pip install --upgrade pip setuptools wheel && pip install aiogram>=3.0.0 openai>=1.0.0 python-dotenv>=1.0.0 langchain>=0.1.0 langchain-openai>=0.0.1 langchain-community>=0.0.1 pypdf>=6.0.0 langchain-ollama>=0.0.1 jq>=1.0.0 ragas>=0.1.0 datasets>=2.14.0 langsmith>=0.1.0 langchain-huggingface>=0.0.1 sentence-transformers>=2.0.0 rank-bm25>=0.2.2 gigachat>=0.1.0 && pip install -e .
```

### Start Command:
```bash
python -m src.app.bot.main
```

**⚠️ Внимание:** Этот способ менее надежен, так как не гарантирует установку всех зависимостей. Рекомендуется использовать Docker.

## Другие частые проблемы

### Проблема: "Dockerfile not found"

**Решение:**
- Убедитесь, что Dockerfile находится в корне репозитория
- Проверьте, что вы закоммитили и запушили Dockerfile в Git
- В поле "Dockerfile Path" укажите `Dockerfile` или оставьте пустым (если файл в корне)

### Проблема: "Build failed"

**Решение:**
1. Проверьте логи сборки в Render Dashboard → Logs
2. Убедитесь, что все зависимости указаны в Dockerfile
3. Проверьте, что Dockerfile синтаксически корректен

### Проблема: "Service crashed"

**Решение:**
1. Проверьте логи в Render Dashboard → Logs
2. Убедитесь, что все переменные окружения установлены:
   - `TELEGRAM_BOT_TOKEN`
   - `OPENAI_API_KEY` (ваш Groq ключ)
3. Проверьте, что команда запуска в Dockerfile правильная: `python -m src.app.bot.main`

### Проблема: Бот не отвечает

**Решение:**
1. Проверьте логи - бот должен быть запущен
2. Убедитесь, что `TELEGRAM_BOT_TOKEN` правильный
3. Проверьте, что бот не заблокирован в Telegram
4. Попробуйте отправить команду `/start` боту

## Нужна помощь?

Если проблема не решена:
1. Проверьте логи в Render Dashboard → Logs
2. Проверьте документацию Render: [render.com/docs](https://render.com/docs)
3. Проверьте, что все файлы (Dockerfile, .dockerignore) закоммичены в Git

