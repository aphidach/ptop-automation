from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from app.config import settings
from app.sheets import repositories

logger = logging.getLogger(__name__)


@dataclass
class BatchProgress:
    batch_id: str
    week: str
    status: str
    expected_meter_count: int
    confirmed_meter_count: int
    missing_meter_ids: list[str]


def generate_batch_id(line_source_id: str) -> str:
    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    week_str = f"{iso[0]}-W{iso[1]:02d}"
    return f"{week_str}-{line_source_id}"


def get_or_create_batch(batch_id: str, line_source_id: str) -> dict:
    existing = repositories.get_batch_by_id(batch_id)
    if existing:
        return existing

    now = datetime.now(timezone.utc)
    iso = now.isocalendar()
    week_str = f"{iso[0]}-W{iso[1]:02d}"

    batch = {
        "batch_id": batch_id,
        "week": week_str,
        "date": now.strftime("%Y-%m-%d"),
        "line_source_id": line_source_id,
        "expected_meter_count": str(settings.EXPECTED_METER_COUNT),
        "confirmed_meter_count": "0",
        "status": "collecting",
        "report_image_url": "",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    repositories.append_batch(batch)
    logger.info("Created batch: %s", batch_id)
    return batch


def get_batch_progress(batch_id: str) -> Optional[BatchProgress]:
    batch = repositories.get_batch_by_id(batch_id)
    if not batch:
        return None

    readings = repositories.get_readings_by_batch(batch_id)
    confirmed_ids = list({r.get("meter_id") for r in readings if r.get("meter_id")})
    confirmed_count = len(confirmed_ids)
    missing = [m for m in settings.VALID_METER_IDS if m not in confirmed_ids]

    return BatchProgress(
        batch_id=batch_id,
        week=batch.get("week", ""),
        status=batch.get("status", "collecting"),
        expected_meter_count=settings.EXPECTED_METER_COUNT,
        confirmed_meter_count=confirmed_count,
        missing_meter_ids=missing,
    )


def update_batch_after_reading(batch_id: str) -> BatchProgress:
    progress = get_batch_progress(batch_id)
    if not progress:
        logger.warning("Cannot update batch '%s': not found", batch_id)
        return BatchProgress(
            batch_id=batch_id,
            week="",
            status="unknown",
            expected_meter_count=settings.EXPECTED_METER_COUNT,
            confirmed_meter_count=0,
            missing_meter_ids=list(settings.VALID_METER_IDS),
        )

    repositories.update_batch_confirmed_count(batch_id, progress.confirmed_meter_count)

    if progress.confirmed_meter_count >= progress.expected_meter_count:
        repositories.update_batch_status(batch_id, "complete")
        progress.status = "complete"

    return progress


def format_progress_message(progress: Optional[BatchProgress]) -> str:
    if progress is None:
        return "ไม่พบข้อมูลรอบนี้ครับ"

    count_text = f"{progress.confirmed_meter_count}/{progress.expected_meter_count}"
    if progress.missing_meter_ids:
        missing_text = ", ".join(progress.missing_meter_ids)
        return f"เก็บแล้ว {count_text} ขาด {missing_text}"
    return f"เก็บครบแล้ว {count_text} 🎉"


def build_progress_message(batch_id: str) -> str:
    return format_progress_message(get_batch_progress(batch_id))
