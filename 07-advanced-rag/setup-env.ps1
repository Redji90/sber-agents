# Скрипт для настройки .env файла
# Использование: .\setup-env.ps1

Write-Host "=== Настройка .env файла ===" -ForegroundColor Cyan
Write-Host ""

# Проверка существования env.example
if (-not (Test-Path "env.example")) {
    Write-Host "Ошибка: файл env.example не найден!" -ForegroundColor Red
    exit 1
}

# Копирование env.example в .env
Copy-Item env.example .env -Force
Write-Host "✓ Файл .env создан из env.example" -ForegroundColor Green
Write-Host ""

# Запрос обязательных переменных
Write-Host "Заполните обязательные переменные:" -ForegroundColor Yellow
Write-Host ""

$telegramToken = Read-Host "Введите TELEGRAM_BOT_TOKEN (или нажмите Enter для пропуска)"
$openaiKey = Read-Host "Введите OPENAI_API_KEY (или нажмите Enter для пропуска)"

# Обновление .env файла
if ($telegramToken -and $telegramToken -ne "") {
    $content = Get-Content .env -Raw
    $content = $content -replace "TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here", "TELEGRAM_BOT_TOKEN=$telegramToken"
    Set-Content .env -Value $content -NoNewline
    Write-Host "✓ TELEGRAM_BOT_TOKEN обновлен" -ForegroundColor Green
}

if ($openaiKey -and $openaiKey -ne "") {
    $content = Get-Content .env -Raw
    $content = $content -replace "OPENAI_API_KEY=your_openai_api_key_here", "OPENAI_API_KEY=$openaiKey"
    Set-Content .env -Value $content -NoNewline
    Write-Host "✓ OPENAI_API_KEY обновлен" -ForegroundColor Green
}

Write-Host ""
Write-Host "=== Готово! ===" -ForegroundColor Green
Write-Host "Файл .env настроен. Теперь вы можете запустить бота: make run" -ForegroundColor Cyan



