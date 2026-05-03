FROM python:3.12-slim AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

FROM python-base AS dependencies
COPY requirements-prod.txt .
RUN pip install --no-cache-dir --no-compile --prefix=/install -r requirements-prod.txt

FROM python-base AS runtime

ARG APP_VERSION=0.3.0
ENV APP_VERSION=${APP_VERSION}
LABEL org.opencontainers.image.title="solar-meter-bot" \
    org.opencontainers.image.description="LINE bot for solar meter OCR reporting" \
    org.opencontainers.image.version="${APP_VERSION}"

RUN apt-get update \
    && apt-get install -y --no-install-recommends fonts-tlwg-garuda \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system appuser \
    && useradd --system --gid appuser --home-dir /app --shell /usr/sbin/nologin appuser \
    && mkdir -p /app/tmp/images /app/tmp/ocr-debug /app/reports /app/credentials /app/data \
    && chown -R appuser:appuser /app

COPY --from=dependencies /install /usr/local
COPY --chown=appuser:appuser app ./app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3).read()"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
