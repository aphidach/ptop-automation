.PHONY: run install

run:
	uv run uvicorn app.main:app --reload --port 8000

install:
	uv sync
