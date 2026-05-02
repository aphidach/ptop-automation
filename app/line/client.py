import logging
from pathlib import Path
from urllib.parse import urlparse

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_LINE_CONTENT_URL = "https://api-data.line.me/v2/bot/message/{message_id}/content"

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

_image_dir = Path(settings.IMAGE_DIR)
_image_dir.mkdir(parents=True, exist_ok=True)


async def download_image(message_id: str) -> Path:
    """Download image from LINE Content API and save to disk.

    Returns the local file path on success.
    Raises ImageDownloadError on failure.
    """
    url = _LINE_CONTENT_URL.format(message_id=message_id)
    headers = {"Authorization": f"Bearer {settings.LINE_CHANNEL_ACCESS_TOKEN}"}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, timeout=30.0)

    if response.status_code != 200:
        logger.error(
            "LINE content API returned %s for message_id=%s",
            response.status_code,
            message_id,
        )
        raise ImageDownloadError(
            f"LINE content API returned {response.status_code} for message_id={message_id}"
        )

    content_type = response.headers.get("content-type", "")
    if content_type.split(";")[0].strip() not in _ALLOWED_CONTENT_TYPES:
        logger.error(
            "Unexpected content type %s for message_id=%s",
            content_type,
            message_id,
        )
        raise ImageDownloadError(
            f"Unexpected content type {content_type} for message_id={message_id}"
        )

    body = response.content
    if len(body) > _MAX_FILE_SIZE:
        logger.error(
            "Image too large (%s bytes) for message_id=%s",
            len(body),
            message_id,
        )
        raise ImageDownloadError(
            f"Image too large ({len(body)} bytes) for message_id={message_id}"
        )

    ext = _content_type_to_ext(content_type)
    file_path = _image_dir / f"{message_id}{ext}"
    file_path.write_bytes(body)
    logger.info("Saved image %s (%s bytes)", file_path, len(body))
    return file_path


def _content_type_to_ext(content_type: str) -> str:
    ct = content_type.split(";")[0].strip()
    mapping = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }
    return mapping.get(ct, ".jpg")


async def push_text(to: str, text: str) -> None:
    """Send a text message via LINE push API (no reply token needed)."""
    from linebot.v3.messaging import (
        AsyncMessagingApi,
        ApiClient,
        Configuration,
        PushMessageRequest,
        TextMessage,
    )

    config = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
    api = AsyncMessagingApi(ApiClient(config))
    try:
        api.push_message(PushMessageRequest(to=to, messages=[TextMessage(text=text)]))
    except Exception:
        logger.exception("Failed to push text message via LINE API to %s", to)


def _is_https_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


async def push_image(to: str, original_url: str, preview_url: str) -> bool:
    """Send an image message via LINE push API (no reply token needed)."""
    from linebot.v3.messaging import (
        AsyncMessagingApi,
        ApiClient,
        Configuration,
        ImageMessage,
        PushMessageRequest,
    )

    if not _is_https_url(original_url) or not _is_https_url(preview_url):
        logger.error(
            "LINE image URLs must be HTTPS: original=%s preview=%s",
            original_url,
            preview_url,
        )
        return False

    config = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
    api = AsyncMessagingApi(ApiClient(config))
    try:
        api.push_message(
            PushMessageRequest(
                to=to,
                messages=[ImageMessage(
                    original_content_url=original_url,
                    preview_image_url=preview_url,
                )],
            )
        )
    except Exception:
        logger.exception("Failed to push image message via LINE API to %s", to)
        return False

    return True


class ImageDownloadError(Exception):
    pass
