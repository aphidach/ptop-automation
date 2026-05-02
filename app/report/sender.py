from __future__ import annotations

import logging
from urllib.parse import urlparse

from app.config import settings
from app.line.client import push_image, push_text
from app.report.generator import generate_report_image
from app.sheets import repositories

logger = logging.getLogger(__name__)


def _build_report_url(filename: str) -> str:
    """Build the public URL for a report image served by the static endpoint."""
    base = settings.APP_BASE_URL.rstrip("/")
    return f"{base}/reports/{filename}"

def _is_https_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


async def send_report(batch_id: str, source_id: str, mark_reported: bool = False) -> bool:
    image_path = generate_report_image(batch_id)
    if not image_path:
        logger.error("Failed to generate report image for batch %s", batch_id)
        await push_text(source_id, "สร้างรูปรายงานไม่สำเร็จครับ พิมพ์ GEN เพื่อลองใหม่")
        return False

    filename = image_path.rsplit("/", 1)[-1]
    original_url = _build_report_url(filename)
    preview_url = original_url
    if not _is_https_url(original_url):
        logger.error("Cannot send LINE image with non-HTTPS report URL: %s", original_url)
        await push_text(
            source_id,
            "สร้างรูปรายงานแล้วครับ\n"
            f"{original_url}\n"
            "ยังส่งเป็นรูปเข้า LINE ไม่ได้ เพราะ APP_BASE_URL ต้องเป็น HTTPS URL สาธารณะ",
        )
        return False

    sent = await push_image(source_id, original_url, preview_url)
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
