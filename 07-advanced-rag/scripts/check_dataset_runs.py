"""Проверка runs, привязанных к датасету."""
import sys
sys.path.insert(0, '.')

from langsmith import Client
from src.app import config

client = Client(api_key=config.LANGSMITH_API_KEY)

print(f"=== Проверка датасета: {config.LANGSMITH_PROJECT} ===\n")

# Получаем информацию о датасете
try:
    dataset = client.read_dataset(dataset_name=config.LANGSMITH_PROJECT)
    print(f"Dataset: {dataset.name} (ID: {dataset.id})")
    
    # Проверяем runs, привязанные к датасету
    runs = list(client.list_runs(dataset_id=dataset.id, limit=10))
    print(f"\nRuns привязанные к датасету: {len(runs)}")
    for run in runs[:5]:
        name = run.name if hasattr(run, 'name') and run.name else 'unnamed'
        print(f"  - {name} (ID: {run.id})")
        if hasattr(run, 'experiment_id'):
            print(f"    Experiment ID: {run.experiment_id}")
    
    # Проверяем runs в проекте
    project_runs = list(client.list_runs(project_name=config.LANGSMITH_PROJECT, limit=10))
    print(f"\nRuns в проекте: {len(project_runs)}")
    for run in project_runs[:5]:
        name = run.name if hasattr(run, 'name') and run.name else 'unnamed'
        print(f"  - {name} (ID: {run.id})")
        if hasattr(run, 'dataset_id'):
            print(f"    Dataset ID: {run.dataset_id}")
        if hasattr(run, 'experiment_id'):
            print(f"    Experiment ID: {run.experiment_id}")
            
except Exception as e:
    print(f"Ошибка: {e}")
    import traceback
    traceback.print_exc()


