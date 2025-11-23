"""Проверка runs и экспериментов в LangSmith."""
from langsmith import Client
from src.app import config

client = Client(api_key=config.LANGSMITH_API_KEY)

print(f"=== Проверка проекта: {config.LANGSMITH_PROJECT} ===\n")

# Проверяем runs
runs = list(client.list_runs(project_name=config.LANGSMITH_PROJECT, limit=10))
print(f"Найдено runs: {len(runs)}")
for run in runs[:5]:
    print(f"  - {run.name or 'unnamed'} (ID: {run.id})")
    if hasattr(run, 'dataset_id'):
        print(f"    Dataset ID: {run.dataset_id}")

# Проверяем датасет
try:
    dataset = client.read_dataset(dataset_name=config.LANGSMITH_PROJECT)
    print(f"\nДатасет найден: {dataset.name} (ID: {dataset.id})")
except Exception as e:
    print(f"\nОшибка при чтении датасета: {e}")

