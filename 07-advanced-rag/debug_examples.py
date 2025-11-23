from src.app.evaluation.evaluation import _load_dataset_from_langsmith, _run_rag_on_dataset
from src.app.indexing.vector_store import get_vector_store_manager

DATASET_NAME = "06-monitoring-qa"

def short(text: str, n: int = 200) -> str:
    text = (text or "").replace("\n", " ")
    return text[:n] + ("..." if len(text) > n else "")

def main() -> None:
    print(f"Загружаю датасет: {DATASET_NAME}")
    dataset = _load_dataset_from_langsmith(DATASET_NAME)
    if dataset is None:
        print("Не удалось загрузить датасет")
        return

    print("Всего примеров в датасете:", len(dataset))

    subset = dataset.select(range(3))

    manager = get_vector_store_manager()
    retriever = manager.get_retriever()

    print("Запускаю RAG на первых 3 примерах...")
    with_rag = _run_rag_on_dataset(subset, retriever)

    for i in range(len(with_rag)):
        ex = with_rag[i]
        q = ex["question"]
        gt_list = ex["ground_truths"] or [""]
        gt = gt_list[0] if gt_list else ""
        ans = ex["answer"]
        ctxs = ex["contexts"] or []

        print(f"\n=== Пример {i+1} ===")
        print("Вопрос:    ", short(q))
        print("Эталон:    ", short(gt))
        print("Ответ RAG: ", short(ans))
        print("Контекст[0]:", short(ctxs[0]) if ctxs else "<нет>")

if __name__ == "__main__":
    main()