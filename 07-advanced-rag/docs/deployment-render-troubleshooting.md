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

## Проблема: "Dockerfile not found" или "failed to read dockerfile: open Dockerfile: no such file or directory"

**Симптомы:**
```
error: failed to solve: failed to read dockerfile: open Dockerfile: no such file or directory
```

**Причины и решения:**

1. **Dockerfile не закоммичен в Git:**
   ```bash
   # Проверьте, что файл есть в репозитории
   git ls-files Dockerfile
   
   # Если файла нет, добавьте его:
   git add Dockerfile .dockerignore render.yaml
   git commit -m "feat: add Dockerfile for deployment"
   git push
   ```

2. **Render не обновил репозиторий:**
   - В Render Dashboard → Settings → Build & Deploy
   - Нажмите "Clear build cache"
   - Нажмите "Manual Deploy" → "Deploy latest commit"

3. **Неправильный путь к Dockerfile:**
   - В настройках сервиса найдите поле "Dockerfile Path"
   - Если Dockerfile в корне проекта: оставьте пустым или укажите `Dockerfile`
   - Если Dockerfile в подпапке: укажите полный путь, например `deploy/Dockerfile`

4. **Root Directory установлен неправильно:**
   - В настройках сервиса проверьте поле "Root Directory"
   - Если проект в корне репозитория: оставьте пустым
   - Если проект в подпапке: укажите путь к папке (например, `07-advanced-rag`)

5. **Проверка в Render:**
   - Убедитесь, что выбран правильный репозиторий
   - Убедитесь, что выбрана правильная ветка (обычно `main` или `master`)
   - Проверьте, что последний коммит содержит Dockerfile

## Проблема: "Deploy failed" - "Exited with status 1"

**Симптомы:**
- В Events видно: "Deploy failed" с красным крестиком
- Ошибка: "Exited with status 1 while building your code"

**Решение:**

1. **Проверьте логи деплоя:**
   - В Render Dashboard откройте раздел **"Logs"**
   - Найдите ошибки в логах сборки (обычно в начале)
   - Скопируйте последние строки с ошибками

2. **Частые причины ошибок:**

   **a) Ошибки установки зависимостей:**
   ```
   ERROR: Could not find a version that satisfies the requirement ...
   ```
   - Проверьте, что все зависимости указаны в Dockerfile
   - Убедитесь, что версии пакетов корректны

   **b) Ошибки компиляции:**
   ```
   error: command 'gcc' failed with exit status 1
   ```
   - Dockerfile должен включать `build-essential` (уже есть в нашем Dockerfile)

   **c) Ошибки импорта:**
   ```
   ModuleNotFoundError: No module named '...'
   ```
   - Проверьте, что все зависимости установлены
   - Убедитесь, что проект установлен: `pip install -e .`

   **d) Ошибки с данными:**
   ```
   FileNotFoundError: [Errno 2] No such file or directory: '@data/...'
   ```
   - Убедитесь, что папка `@data` скопирована в Docker образ (в Dockerfile есть `COPY . .`)

3. **Как исправить:**
   - Исправьте ошибку в коде/Dockerfile
   - Закоммитьте изменения: `git add . && git commit -m "fix: ..." && git push`
   - Render автоматически запустит новый деплой

4. **Если не можете найти ошибку:**
   - Скопируйте последние 50-100 строк из логов
   - Проверьте, что все файлы закоммичены в Git
   - Убедитесь, что Dockerfile корректен

## Проблема: Деплой завис на "Deploy started"

**Симптомы:**
- Деплой показывает "Deploy started" с крутящимся индикатором
- Прошло больше 10-15 минут

**Решение:**

1. **Подождите еще 5-10 минут** (первая сборка может занять время)

2. **Проверьте логи:**
   - Откройте раздел "Logs"
   - Посмотрите, есть ли активность (новые строки появляются)

3. **Если деплой действительно завис:**
   - Нажмите "Cancel deploy"
   - Проверьте логи на наличие ошибок
   - Попробуйте "Manual Deploy" → "Deploy latest commit"

## Проблема: Бот не отвечает после успешного деплоя

**Решение:**
1. Проверьте логи в Render Dashboard → Logs
2. Убедитесь, что все переменные окружения установлены:
   - `TELEGRAM_BOT_TOKEN`
   - `OPENAI_API_KEY` (ваш Groq ключ)
3. Проверьте, что бот не заблокирован в Telegram
4. Попробуйте отправить команду `/start` боту
5. Проверьте логи на наличие ошибок подключения к Telegram API

## Проблема: "Port scan timeout reached, no open ports detected"

**Симптомы:**
```
==> Port scan timeout reached, no open ports detected. 
Bind your service to at least one port. If you don't need to receive traffic on any port, 
create a background worker instead.
```

**Причина:**
Вы создали **Web Service** вместо **Background Worker**. Web Service должен слушать HTTP порт, а Telegram-бот работает через polling и не слушает порт.

**Решение:**

1. **Удалите текущий Web Service:**
   - В Render Dashboard откройте настройки сервиса
   - Прокрутите вниз до раздела "Delete"
   - Нажмите "Delete" и подтвердите

2. **Создайте Background Worker:**
   - Нажмите "New +" → **"Background Worker"** (не Web Service!)
   - Выберите тот же репозиторий и ветку
   - Настройте так же, как Web Service:
     - Environment: Docker
     - Root Directory: `07-advanced-rag` (если проект в подпапке)
     - Dockerfile Path: `Dockerfile` или оставьте пустым
     - Добавьте те же переменные окружения
   - Нажмите "Create Background Worker"

3. **Проверьте работу:**
   - Дождитесь завершения деплоя
   - Проверьте логи - не должно быть ошибок про порт
   - Протестируйте бота в Telegram

**Альтернатива (не рекомендуется):**
Если по какой-то причине нужно использовать Web Service, можно добавить простой HTTP сервер в код, но это не нужно для Telegram-бота.

## Нужна помощь?

Если проблема не решена:
1. Проверьте логи в Render Dashboard → Logs
2. Проверьте документацию Render: [render.com/docs](https://render.com/docs)
3. Проверьте, что все файлы (Dockerfile, .dockerignore) закоммичены в Git
4. Скопируйте последние строки логов с ошибками для анализа
