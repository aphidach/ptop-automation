VERSION ?= 0.1.1
IMAGE ?= solar-meter-bot
PORT ?= 8000
DOCKER_RUN_ENV ?= .env

.PHONY: run install test ocr-test package wheel docker-build docker-run release-tag richmenu-check richmenu-validate richmenu-upload

run:
	uv run uvicorn app.main:app --reload --port 8000

install:
	uv sync --extra dev

test:
	uv run --extra dev pytest

ocr-test:
	uv run python scripts/evaluate_ocr.py

package: wheel docker-build

wheel:
	uv build --wheel

docker-build:
	docker build --build-arg APP_VERSION=$(VERSION) -t $(IMAGE):$(VERSION) -t $(IMAGE):latest .

docker-run:
	docker run --rm --env-file $(DOCKER_RUN_ENV) -p $(PORT):8000 $(IMAGE):$(VERSION)

release-tag:
	@test -z "$$(git status --porcelain)" || (echo "Commit or stash changes before tagging v$(VERSION)." >&2; exit 1)
	git tag -a v$(VERSION) -m "Release v$(VERSION)"

richmenu-check:
	uv run python scripts/upload_richmenu.py --local-only

richmenu-validate:
	uv run python scripts/upload_richmenu.py

richmenu-upload:
	uv run python scripts/upload_richmenu.py --apply --set-default
