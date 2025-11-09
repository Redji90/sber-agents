.PHONY: install run lint format clean

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
