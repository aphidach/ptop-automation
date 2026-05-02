from __future__ import annotations

from dataclasses import dataclass
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
    report_image_url: str = ""


def get_current_batch_summary(source_id: str, session_batch_id: str | None = None) -> BatchSummary | None:
    batch_id = session_batch_id or generate_batch_id(source_id)
    return get_batch_summary(batch_id)


def get_previous_batch_summary(source_id: str, current_batch_id: str | None = None) -> BatchSummary | None:
    batches = repositories.get_batches_by_source(source_id)
    for batch in batches:
        batch_id = str(batch.get("batch_id", ""))
        if current_batch_id and batch_id == current_batch_id:
            continue
        return get_batch_summary(batch_id)
    return None


def get_latest_report_batch_id(source_id: str) -> str | None:
    for batch in repositories.get_batches_by_source(source_id):
        if str(batch.get("report_image_url", "")).strip():
            return str(batch.get("batch_id", ""))
    latest = repositories.get_batches_by_source(source_id)
    if latest:
        return str(latest[0].get("batch_id", "")) or None
    return None


def get_batch_summary(batch_id: str) -> BatchSummary | None:
    batch = repositories.get_batch_by_id(batch_id)
    if not batch:
        return None

    readings = repositories.get_readings_by_batch(batch_id)
    confirmed_ids = {str(r.get("meter_id", "")) for r in readings if r.get("meter_id")}
    missing = [m for m in settings.VALID_METER_IDS if m not in confirmed_ids]
    expected = _to_int(batch.get("expected_meter_count"), settings.EXPECTED_METER_COUNT)

    return BatchSummary(
        batch_id=str(batch.get("batch_id", batch_id)),
        week=str(batch.get("week", "")),
        status=str(batch.get("status", "")) or "collecting",
        expected_meter_count=expected,
        confirmed_meter_count=len(confirmed_ids),
        missing_meter_ids=missing,
        produced_unit=sum((_to_decimal(r.get("produced_unit")) for r in readings), Decimal("0")),
        amount=sum((_to_decimal(r.get("amount")) for r in readings), Decimal("0")),
        readings=sorted(readings, key=lambda r: str(r.get("meter_id", ""))),
        report_image_url=str(batch.get("report_image_url", "")),
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
