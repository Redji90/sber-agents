# Скрипт для замены секрета в истории через git filter-branch
$env:FILTER_BRANCH_SQUELCH_WARNING=1

# Создаём временный скрипт для замены
$script = @'
import sys
import re
import json

file_path = sys.argv[1]
if not os.path.exists(file_path):
    sys.exit(0)

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Заменяем секрет
content = re.sub(r'lsv2_pt_[a-zA-Z0-9_]+', 'YOUR_LANGCHAIN_API_KEY_HERE', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)
'@

# Используем git filter-branch с Python скриптом
git filter-branch --force --tree-filter "python -c `"$script`" '08-agents-langgraph/docs/references/naive-rag.ipynb' 2>/dev/null || echo 'File not found or already processed'" --prune-empty --tag-name-filter cat -- --all

