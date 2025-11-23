# Скрипт для настройки пути сохранения моделей Ollama на другой диск
# Использование: .\setup_ollama_models.ps1 D:\Ollama\Models

param(
    [Parameter(Mandatory=$true)]
    [string]$ModelsPath
)

# Проверяем, что путь существует или создаем его
if (-not (Test-Path $ModelsPath)) {
    Write-Host "Создаю директорию: $ModelsPath"
    New-Item -ItemType Directory -Path $ModelsPath -Force | Out-Null
}

# Устанавливаем переменную окружения для текущей сессии
$env:OLLAMA_MODELS = $ModelsPath
Write-Host "OLLAMA_MODELS установлен в: $env:OLLAMA_MODELS"

# Устанавливаем переменную окружения глобально для пользователя
[System.Environment]::SetEnvironmentVariable("OLLAMA_MODELS", $ModelsPath, "User")
Write-Host "OLLAMA_MODELS установлен глобально для пользователя"

Write-Host ""
Write-Host "Доступные быстрые модели для скачивания:"
Write-Host "  - llama3.2:1b-instruct-q4_K_M  (самая быстрая, ~700MB)"
Write-Host "  - llama3.2:3b-instruct-q4_K_M  (быстрая, ~2GB)"
Write-Host "  - mistral:7b-instruct-q4_K_M   (хорошее качество, ~4.5GB)"
Write-Host "  - phi3:mini (Microsoft, очень быстрая, ~2.3GB)"
Write-Host ""
Write-Host "Для скачивания используйте:"
Write-Host "  ollama pull llama3.2:1b-instruct-q4_K_M"
Write-Host "  (или другую модель из списка)"
Write-Host ""
Write-Host "ВАЖНО: Перезапустите Ollama сервис после установки переменной окружения!"


