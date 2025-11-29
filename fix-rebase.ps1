# Скрипт для автоматического rebase с редактированием коммита e314bed
$rebaseTodo = ".git/rebase-merge/git-rebase-todo"
$tempFile = ".git/rebase-merge/git-rebase-todo.tmp"

# Создаём todo list для rebase
$content = @"
edit e314bed Выполнено ДЗ-8: ReAct агенты с LangChain
pick f938fe8 ыавыав
pick cb6c09a HW-10: guard bank agent with PII masking, HITL and rate limiting
pick 97c81b9 10
pick 6e9541a 10
pick dde97d9 08
"@

# Создаём директорию если нужно
New-Item -ItemType Directory -Force -Path ".git/rebase-merge" | Out-Null
Set-Content -Path $rebaseTodo -Value $content

Write-Host "Rebase todo list created. Now run: git rebase --continue"
Write-Host "Then edit the file and run: git add ... && git commit --amend && git rebase --continue"

