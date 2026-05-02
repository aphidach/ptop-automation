.PHONY: run install richmenu-check richmenu-validate richmenu-upload

run:
	uv run uvicorn app.main:app --reload --port 8000

install:
	uv sync

richmenu-check:
	uv run python scripts/upload_richmenu.py --local-only

richmenu-validate:
	uv run python scripts/upload_richmenu.py

richmenu-upload:
	uv run python scripts/upload_richmenu.py --apply --set-default
