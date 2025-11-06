# Настройка Ollama для локального использования

## Шаг 1: Установка Ollama

### Windows
1. Скачайте установщик с https://ollama.com/download
2. Запустите установщик и следуйте инструкциям
3. Ollama установится как сервис и будет доступен на `http://localhost:11434`

### Linux/Mac
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

## Шаг 2: Установка моделей

Для работы с текстом (LLM):
```bash
ollama pull llama3.2:latest
# или
ollama pull mistral:latest
# или
ollama pull qwen2.5:latest
```

Для работы с изображениями (VLM):
```bash
ollama pull llava:latest
# или
ollama pull qwen2.5-vl:latest
```

## Шаг 3: Проверка работы

Убедитесь, что Ollama запущен:
```bash
ollama serve
```

Или проверьте, что сервис работает:
```bash
curl http://localhost:11434/api/tags
```

## Шаг 4: Настройка config.yaml

Обновите `config.yaml`:

```yaml
telegram:
  bot_token: "ваш_токен_бота"

llm:
  provider: "ollama"
  model: "llama3.2:latest"  # или другая установленная модель
  api_key: ""  # не требуется для Ollama
  base_url: "http://localhost:11434/v1"

vlm:
  provider: "ollama"
  model: "llava:latest"  # или другая vision модель
  api_key: ""  # не требуется для Ollama
  base_url: "http://localhost:11434/v1"

storage:
  type: "json"
  path: "data/transactions.json"
```

## Шаг 5: Запуск бота

```bash
make run
```

## Примечания

- Ollama должен быть запущен перед запуском бота
- Для Windows Ollama обычно запускается автоматически как сервис
- Для Linux/Mac может потребоваться запустить `ollama serve` в отдельном терминале
- Убедитесь, что порт 11434 доступен и не заблокирован файрволом

## Настройка SSH ключа для виртуального сервера (immers.cloud)

### Windows

После скачивания PEM ключа с платформы immers.cloud:

1. **Создайте директорию `.ssh` в домашней папке (если её ещё нет):**
   ```powershell
   New-Item -ItemType Directory -Force -Path $HOME\.ssh
   ```

2. **Сохраните ключ в `$HOME\.ssh\immers-vm.pem`**

3. **Установите права доступа (только для текущего пользователя):**
   
   В PowerShell выполните:
   ```powershell
   icacls $HOME\.ssh\immers-vm.pem /inheritance:r
   icacls $HOME\.ssh\immers-vm.pem /grant:r "$env:USERNAME`:R"
   ```
   
   Или через свойства файла:
   - Правой кнопкой мыши на файл → Свойства → Безопасность
   - Убедитесь, что доступ есть только у вашего пользователя
   - Удалите все остальные пользователи/группы

4. **Проверьте подключение:**
   ```powershell
   ssh -i $HOME\.ssh\immers-vm.pem root@<IP-адрес-сервера>
   ```

### Linux/Mac

```bash
# Сохраните ключ в ~/.ssh/immers-vm.pem
# Установите права:
chmod 600 ~/.ssh/immers-vm.pem

# Подключитесь:
ssh -i ~/.ssh/immers-vm.pem root@<IP-адрес-сервера>
```

### Примечание

**Ошибка `chmod: Имя "chmod" не распознано`** в Windows возникает потому, что `chmod` — это Unix/Linux команда. В Windows используйте команду `icacls` или настройте права через свойства файла (правый клик → Свойства → Безопасность).

