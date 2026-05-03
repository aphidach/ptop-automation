from __future__ import annotations

import logging
import time
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from app.config import settings
from app.line.client import push_image, push_message, push_text
from app.line.messages import build_report_unavailable_message
from app.report.generator import generate_report_image
from app.sheets import repositories
from app.storage.r2 import R2ConfigError, R2UploadError, upload_report_image

logger = logging.getLogger(__name__)


def _build_report_url(filename: str) -> str:
    """Build the public URL for a report image served by the static endpoint."""
    base = settings.APP_BASE_URL.rstrip("/")
    return f"{base}/reports/{filename}"


def _uses_r2_report_storage() -> bool:
    return settings.REPORT_IMAGE_STORAGE.lower() == "r2"


def _report_url_setting_name() -> str:
    return "R2_PUBLIC_URL" if _uses_r2_report_storage() else "APP_BASE_URL"


def _is_https_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _build_report_delivery_url(image_path: str) -> str:
    if _uses_r2_report_storage():
        return upload_report_image(image_path)

    return _build_report_url(Path(image_path).name)


def _cache_bust_report_url(url: str, version: int | str | None = None) -> str:
    parsed = urlparse(url)
    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if key != "v"
    ]
    query.append(("v", str(version if version is not None else time.time_ns())))
    return urlunparse(parsed._replace(query=urlencode(query)))


async def send_report(batch_id: str, source_id: str, mark_reported: bool = False) -> bool:
    image_path = generate_report_image(batch_id)
    if not image_path:
        logger.error("Failed to generate report image for batch %s", batch_id)
        await push_message(
            source_id,
            build_report_unavailable_message(
                batch_id=batch_id,
                reason="สร้างรูปรายงานไม่สำเร็จ",
            ),
        )
        return False

    try:
        original_url = _build_report_delivery_url(image_path)
    except (R2ConfigError, R2UploadError) as exc:
        logger.error("Cannot upload report image for batch %s: %s", batch_id, exc)
        await push_text(
            source_id,
            "สร้างรูปรายงานแล้วครับ แต่อัปโหลดไป R2 ไม่สำเร็จ\n"
            "กรุณาตรวจสอบค่า R2 แล้วลองพิมพ์ REPORT อีกครั้ง",
        )
        return False

    if not _is_https_url(original_url):
        logger.error("Cannot send LINE image with non-HTTPS report URL: %s", original_url)
        await push_text(
            source_id,
            "สร้างรูปรายงานแล้วครับ\n"
            f"{original_url}\n"
            f"ยังส่งเป็นรูปเข้า LINE ไม่ได้ เพราะ {_report_url_setting_name()} ต้องเป็น HTTPS URL สาธารณะ",
        )
        return False

    delivery_url = _cache_bust_report_url(original_url)
    preview_url = delivery_url
    repositories.update_batch_report_image_url(batch_id, original_url)
    sent = await push_image(source_id, delivery_url, preview_url)
    if not sent:
        await push_text(
            source_id,
            "ส่งรูปรายงานเข้า LINE ไม่สำเร็จครับ\n"
            f"{original_url}\n"
            "กรุณาลองพิมพ์ REPORT อีกครั้ง",
        )
        return False

    if mark_reported:
        repositories.update_batch_status(batch_id, "reported")
    logger.info("Report sent for batch %s", batch_id)
    return True


async def send_report_if_complete(batch_id: str, source_id: str) -> None:
    """If batch is complete, generate report image and send it to LINE.

    Called after each confirmed reading. Only acts when all meters are confirmed.
    """
    progress = repositories.get_batch_by_id(batch_id)
    if not progress:
        return

    status = progress.get("status", "")
    if status != "complete":
        return

    await send_report(batch_id, source_id, mark_reported=True)
