from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from app.config import settings
from app.services.batch_service import generate_batch_id
from app.sheets import repositories


@dataclass
class BatchSummary:
    batch_id: str
    week: str
    status: str
    expected_meter_count: int
    confirmed_meter_count: int
    missing_meter_ids: list[str]
    produced_unit: Decimal
    amount: Decimal
    readings: list[dict]
    date: str = ""
    created_at: str = ""
    updated_at: str = ""
    report_image_url: str = ""


def get_current_batch_summary(source_id: str, session_batch_id: str | None = None) -> BatchSummary | None:
    batch_id = session_batch_id or generate_batch_id(source_id)
    return get_batch_summary(batch_id)


def get_previous_batch_summary(source_id: str, current_batch_id: str | None = None) -> BatchSummary | None:
    current_batch_id = current_batch_id or generate_batch_id(source_id)
    batches = repositories.get_batches_by_source(source_id)
    for batch in batches:
        batch_id = str(batch.get("batch_id", ""))
        if batch_id == current_batch_id:
            continue
        return get_batch_summary(batch_id)
    return None


def get_recent_batch_summaries(
    source_id: str,
    *,
    days: int = 31,
    limit: int = 5,
    now: datetime | None = None,
) -> list[BatchSummary]:
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=days)
    batch_refs: dict[str, datetime] = {}

    for batch in repositories.get_batches_by_source(source_id):
        batch_id = str(batch.get("batch_id", "")).strip()
        if not batch_id:
            continue
        seen_at = _row_datetime(batch)
        if seen_at and seen_at >= cutoff:
            batch_refs[batch_id] = seen_at

    for reading in repositories.get_readings_by_source(source_id):
        batch_id = str(reading.get("batch_id", "")).strip()
        if not batch_id:
            continue
        seen_at = _row_datetime(reading)
        if seen_at and seen_at >= cutoff:
            current = batch_refs.get(batch_id)
            if current is None or seen_at > current:
                batch_refs[batch_id] = seen_at

    summaries = []
    for batch_id, seen_at in sorted(batch_refs.items(), key=lambda item: item[1], reverse=True):
        summary = get_batch_summary(batch_id)
        if summary:
            summaries.append(summary)
        if len(summaries) >= limit:
            break
    return summaries


def get_latest_report_batch_id(source_id: str) -> str | None:
    batches = repositories.get_batches_by_source(source_id)
    for batch in batches:
        if str(batch.get("report_image_url", "")).strip():
            return str(batch.get("batch_id", "")) or None
    for batch in batches:
        if _has_report_data(batch):
            return str(batch.get("batch_id", "")) or None
    return None


def _has_report_data(batch: dict) -> bool:
    batch_id = str(batch.get("batch_id", "")).strip()
    if not batch_id:
        return False
    readings = repositories.get_readings_by_batch(batch_id)
    if not readings:
        return False
    confirmed_ids = {str(r.get("meter_id", "")) for r in readings if r.get("meter_id")}
    expected = _to_int(batch.get("expected_meter_count"), settings.EXPECTED_METER_COUNT)
    status = str(batch.get("status", "")).strip().lower()
    return status in {"complete", "reported"} or len(confirmed_ids) >= expected


def get_batch_summary(batch_id: str) -> BatchSummary | None:
    batch = repositories.get_batch_by_id(batch_id)
    readings = repositories.get_readings_by_batch(batch_id)
    if not batch and not readings:
        return None

    confirmed_ids = {str(r.get("meter_id", "")) for r in readings if r.get("meter_id")}
    expected = _to_int(batch.get("expected_meter_count") if batch else None, settings.EXPECTED_METER_COUNT)
    missing = [m for m in settings.VALID_METER_IDS if m not in confirmed_ids]
    first_reading = readings[0] if readings else {}
    status = str(batch.get("status", "") if batch else "") or (
        "complete" if len(confirmed_ids) >= expected else "collecting"
    )

    return BatchSummary(
        batch_id=str(batch.get("batch_id", batch_id) if batch else batch_id),
        week=str(batch.get("week", "") if batch else first_reading.get("week", "")) or _week_from_batch_id(batch_id),
        status=status,
        expected_meter_count=expected,
        confirmed_meter_count=len(confirmed_ids),
        missing_meter_ids=missing,
        produced_unit=sum((_to_decimal(r.get("produced_unit")) for r in readings), Decimal("0")),
        amount=sum((_to_decimal(r.get("amount")) for r in readings), Decimal("0")),
        readings=sorted(readings, key=lambda r: str(r.get("meter_id", ""))),
        date=str(batch.get("date", "") if batch else first_reading.get("date", "")),
        created_at=str(batch.get("created_at", "") if batch else first_reading.get("created_at", "")),
        updated_at=str(batch.get("updated_at", "") if batch else ""),
        report_image_url=str(batch.get("report_image_url", "") if batch else ""),
    )


def get_meter_history(meter_id: str, source_id: str, limit: int = 3) -> list[dict]:
    return repositories.get_readings_by_meter(meter_id, source_id)[:limit]


def _to_decimal(value) -> Decimal:
    try:
        return Decimal(str(value or "0").replace(",", ""))
    except (InvalidOperation, ValueError):
        return Decimal("0")


def _to_int(value, fallback: int) -> int:
    try:
        return int(str(value or "").strip())
    except ValueError:
        return fallback


def _row_datetime(row: dict) -> datetime | None:
    for key in ("date", "created_at", "updated_at"):
        parsed = _parse_datetime(row.get(key))
        if parsed:
            return parsed
    return None


def _parse_datetime(value) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(text, "%Y-%m-%d")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _week_from_batch_id(batch_id: str) -> str:
    parts = str(batch_id).split("-")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].upper().startswith("W"):
        return f"{parts[0]}-{parts[1].upper()}"
    return ""
