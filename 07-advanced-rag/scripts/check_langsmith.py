"""Проверка runs и экспериментов в LangSmith."""
import sys
sys.path.insert(0, '.')

from langsmith import Client
from src.app import config

client = Client(api_key=config.LANGSMITH_API_KEY)

print(f"=== Проверка проекта: {config.LANGSMITH_PROJECT} ===\n")

# Проверяем runs
runs = list(client.list_runs(project_name=config.LANGSMITH_PROJECT, limit=10))
print(f"Найдено runs: {len(runs)}")
for run in runs[:5]:
    name = run.name if hasattr(run, 'name') and run.name else 'unnamed'
    print(f"  - {name} (ID: {run.id})")

# Проверяем датасет
try:
    dataset = client.read_dataset(dataset_name=config.LANGSMITH_PROJECT)
    print(f"\nДатасет найден: {dataset.name} (ID: {dataset.id})")
except Exception as e:
    print(f"\nОшибка при чтении датасета: {e}")

