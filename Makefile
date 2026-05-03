VERSION ?= 0.3.0
IMAGE ?= solar-meter-bot
PORT ?= 8000
DOCKER_RUN_ENV ?= .env
GITLEAKS_IMAGE ?= ghcr.io/gitleaks/gitleaks:v8.30.1

.PHONY: run install test secrets-scan ocr-test package wheel docker-build docker-run release-tag richmenu-check richmenu-validate richmenu-upload

run:
	uv run uvicorn app.main:app --reload --port 8000

install:
	uv sync --extra dev

test:
	uv run --extra dev pytest

secrets-scan:
	@if command -v gitleaks >/dev/null 2>&1; then \
		gitleaks git --redact --verbose --log-opts="--all" .; \
	elif command -v docker >/dev/null 2>&1; then \
		docker run --rm -v "$$(pwd):/repo" -w /repo $(GITLEAKS_IMAGE) git --redact --verbose --log-opts="--all" /repo; \
	else \
		echo "Install gitleaks or Docker to run secrets-scan." >&2; \
		exit 127; \
	fi

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
