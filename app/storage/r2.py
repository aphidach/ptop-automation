from __future__ import annotations

import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

REPORT_PREFIX = "reports"


class R2ConfigError(Exception):
    pass


class R2UploadError(Exception):
    pass


def upload_report_image(image_path: str | Path) -> str:
    path = Path(image_path)
    if not path.exists():
        raise R2UploadError(f"Report image not found: {path}")

    _validate_config()
    key = f"{REPORT_PREFIX}/{path.name}"

    try:
        import boto3
        from botocore.exceptions import BotoCoreError, ClientError
    except ImportError as exc:
        raise R2UploadError("boto3 is required for R2 report uploads") from exc

    client = boto3.client(
        "s3",
        endpoint_url=settings.R2_ENDPOINT,
        aws_access_key_id=settings.R2_ACCESS_KEY_ID,
        aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )

    try:
        client.upload_file(
            str(path),
            settings.R2_BUCKET,
            key,
            ExtraArgs={"ContentType": "image/png"},
        )
    except (BotoCoreError, ClientError, OSError) as exc:
        raise R2UploadError(f"Failed to upload report image to R2: {path}") from exc

    url = _build_public_url(key)
    logger.info("Uploaded report image to R2: %s", url)
    return url


def _validate_config() -> None:
    missing = [
        name
        for name in (
            "R2_ENDPOINT",
            "R2_ACCESS_KEY_ID",
            "R2_SECRET_ACCESS_KEY",
            "R2_BUCKET",
            "R2_PUBLIC_URL",
        )
        if not getattr(settings, name)
    ]
    if missing:
        raise R2ConfigError(f"Missing R2 config: {', '.join(missing)}")


def _build_public_url(key: str) -> str:
    base = settings.R2_PUBLIC_URL.rstrip("/")
    return f"{base}/{key}"
