# Скрипт для исправления кодировки в .env файле
# Запустите этот скрипт после остановки бота

$envFile = ".env"

# Проверяем существование файла
if (-not (Test-Path $envFile)) {
    Write-Host "Файл .env не найден!"
    exit 1
}

# Читаем файл
$content = Get-Content $envFile -Raw -Encoding UTF8

# Исправляем кракозябры в SYSTEM_ROLE
$content = $content -replace 'SYSTEM_ROLE=.*', 'SYSTEM_ROLE=банковский ассистент'

# Сохраняем файл в UTF-8
$content | Set-Content $envFile -Encoding UTF8 -NoNewline

Write-Host "Файл .env исправлен! Значение SYSTEM_ROLE установлено в 'банковский ассистент'"


