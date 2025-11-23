.PHONY: install run lint format clean download-model evaluate dataset dataset-upload reindex

install:
	uv venv
	uv pip install -e .

run: install
	@echo "Running bot module in .venv..."
	uv run python -m src.app.bot.main

lint:
	uv run ruff check src/

format:
	uv run black src/

clean:
	rm -rf .venv
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

download-model:
	@echo "Downloading HuggingFace model..."
	@echo "Usage: make download-model CACHE_FOLDER=D:\\huggingface_cache"
	@if [ -n "$(CACHE_FOLDER)" ]; then \
		uv run python scripts/download_model.py --cache-folder "$(CACHE_FOLDER)"; \
	else \
		uv run python scripts/download_model.py; \
	fi

evaluate:
	@echo "Running RAG evaluation..."
	@echo "This will evaluate the RAG pipeline using the dataset from LangSmith."
	@echo "Note: This requires the index to be built in the same process."
	@echo "If index is empty, use 'make reindex-and-evaluate' instead."
	uv run python scripts/run_evaluation.py

reindex-and-evaluate:
	@echo "Reindexing and evaluating in one process..."
	@echo "This will rebuild the index and run evaluation."
	uv run python scripts/reindex_and_evaluate.py

reindex:
	@echo "Reindexing documents..."
	@echo "This will rebuild the vector store index from @data directory."
	uv run python scripts/reindex.py

dataset:
	@echo "Synthesizing dataset from documents..."
	@echo "This will generate Q&A pairs from documents in @data directory."
	uv run python -c "from src.app.synthesis.dataset_synthesizer import synthesize_dataset; synthesize_dataset(upload_to_langsmith=False)"

dataset-upload:
	@echo "Synthesizing and uploading dataset to LangSmith..."
	@echo "This will generate Q&A pairs and upload them to LangSmith."
	uv run python -c "from src.app.synthesis.dataset_synthesizer import synthesize_dataset; synthesize_dataset(upload_to_langsmith=True)"
