# Dockerfile для деплоя Telegram-бота
FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Рабочая директория
WORKDIR /app

# Копирование файлов зависимостей
COPY pyproject.toml ./

# Установка зависимостей через pip (проще для деплоя)
# Используем --root-user-action=ignore чтобы убрать предупреждение о root пользователе
RUN pip install --no-cache-dir --upgrade pip setuptools wheel --root-user-action=ignore && \
    pip install --no-cache-dir --root-user-action=ignore \
    aiogram>=3.0.0 \
    openai>=1.0.0 \
    python-dotenv>=1.0.0 \
    langchain>=0.1.0 \
    langchain-openai>=0.0.1 \
    langchain-community>=0.0.1 \
    pypdf>=6.0.0 \
    langchain-ollama>=0.0.1 \
    jq>=1.0.0 \
    ragas>=0.1.0 \
    datasets>=2.14.0 \
    langsmith>=0.1.0 \
    langchain-huggingface>=0.0.1 \
    sentence-transformers>=2.0.0 \
    rank-bm25>=0.2.2 \
    gigachat>=0.1.0

# Копирование всего проекта (включая данные)
COPY . .

# Установка проекта в режиме разработки
RUN pip install --no-cache-dir -e .

# Запуск бота
CMD ["python", "-m", "src.app.bot.main"]

