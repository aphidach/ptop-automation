from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.config import settings
from app.sheets import repositories

logger = logging.getLogger(__name__)

READING_VALUE_PRECISION = Decimal("0.1")


@dataclass
class ReadingCalculation:
    last_value: Decimal
    produced_unit: Decimal
    rate: Decimal
    amount: Decimal


@dataclass
class ValidationResult:
    is_valid: bool
    warnings: list[str]


def calculate_reading(
    meter_id: str,
    current_value: Decimal,
    line_source_id: str | None = None,
) -> ReadingCalculation:
    """Calculate produced_unit and amount from current_value and last reading."""
    last_value = _get_last_value(meter_id, line_source_id)
    rate = _get_rate(meter_id)
    produced_unit = current_value - last_value
    amount = produced_unit * rate
    return ReadingCalculation(
        last_value=last_value,
        produced_unit=produced_unit,
        rate=rate,
        amount=amount,
    )


def validate_reading(
    meter_id: str,
    current_value: Decimal,
    batch_id: str,
    allow_duplicate: bool = False,
    allow_lower_value: bool = False,
    line_source_id: str | None = None,
) -> ValidationResult:
    """Validate a reading before saving. Returns warnings for edge cases."""
    warnings: list[str] = []

    existing = _existing_reading_in_batch(meter_id, batch_id)
    last_value = _decimal_from_row(existing.get("last_value")) if allow_duplicate and existing else None
    if last_value is None:
        last_value = _get_last_value(meter_id, line_source_id)
    if current_value < last_value and not allow_lower_value:
        warnings.append(
            f"ค่าปัจจุบัน ({current_value}) น้อยกว่าค่าครั้งก่อน ({last_value})"
        )

    if existing and not allow_duplicate:
        warnings.append(
            f"มิเตอร์ {meter_id} ถูกบันทึกไปแล้วในรอบนี้ ต้องการแทนที่หรือไม่?"
        )

    is_valid = len(warnings) == 0
    return ValidationResult(is_valid=is_valid, warnings=warnings)


def save_reading(
    meter_id: str,
    current_value: Decimal,
    batch_id: str,
    line_source_id: str,
    line_user_id: str = "",
    ocr_raw_text: str = "",
    ocr_value: Optional[Decimal] = None,
    confirmation_method: str = "ok",
    image_message_id: str = "",
    replace_existing: bool = False,
) -> ReadingCalculation:
    """Calculate, build reading dict, and append to Google Sheets."""
    current_value = normalize_reading_value(current_value)
    existing = _existing_reading_in_batch(meter_id, batch_id) if replace_existing else None
    calc = (
        _calculate_replacement_reading(meter_id, current_value, existing, line_source_id)
        if existing
        else calculate_reading(meter_id, current_value, line_source_id)
    )

    now = _now()
    date_str = now.strftime("%Y-%m-%d")
    week_str = _iso_week(now)
    reading_id = str(existing.get("reading_id", "")).strip() if existing else ""
    if not reading_id:
        reading_id = f"rdg_{now.strftime('%Y%m%d')}_{batch_id}_{meter_id}"

    reading = {
        "reading_id": reading_id,
        "batch_id": batch_id,
        "date": date_str,
        "week": week_str,
        "line_source_id": line_source_id,
        "line_user_id": line_user_id,
        "meter_id": meter_id,
        "current_value": format_reading_value(current_value),
        "last_value": str(calc.last_value),
        "produced_unit": str(calc.produced_unit),
        "rate": str(calc.rate),
        "amount": str(calc.amount),
        "ocr_raw_text": ocr_raw_text,
        "ocr_value": str(ocr_value) if ocr_value is not None else "",
        "confirmation_method": confirmation_method,
        "image_message_id": image_message_id,
        "image_file_id": "",
        "created_at": now.isoformat(),
    }

    if replace_existing:
        repositories.upsert_reading(reading)
    else:
        repositories.append_reading(reading)
    logger.info(
        "%s reading: meter=%s current=%s last=%s unit=%s amount=%s",
        "Replaced" if replace_existing else "Saved",
        meter_id,
        current_value,
        calc.last_value,
        calc.produced_unit,
        calc.amount,
    )
    return calc


def normalize_reading_value(value: Decimal) -> Decimal:
    return Decimal(str(value)).quantize(READING_VALUE_PRECISION, rounding=ROUND_HALF_UP)


def format_reading_value(value: Decimal) -> str:
    return str(normalize_reading_value(value))


def _get_last_value(meter_id: str, line_source_id: str | None = None) -> Decimal:
    """Get the latest confirmed current_value for a meter. Returns 0 if no previous reading."""
    latest = repositories.get_latest_reading(meter_id, line_source_id)
    if latest is None:
        return Decimal(0)
    raw = latest.get("current_value", 0)
    return Decimal(str(raw))


def _get_rate(meter_id: str) -> Decimal:
    """Get rate from meter master data, fallback to DEFAULT_RATE."""
    sheet_default = _get_default_rate_setting()
    meter = repositories.get_meter_by_id(meter_id)
    if meter and meter.get("default_rate", "") != "":
        raw = meter.get("default_rate", sheet_default)
    else:
        raw = sheet_default
    return Decimal(str(raw))


def _is_duplicate_in_batch(meter_id: str, batch_id: str) -> bool:
    """Check if meter_id already exists in the given batch."""
    return _existing_reading_in_batch(meter_id, batch_id) is not None


def _existing_reading_in_batch(meter_id: str, batch_id: str) -> dict | None:
    readings = repositories.get_readings_by_batch(batch_id)
    for reading in readings:
        if reading.get("meter_id") == meter_id:
            return reading
    return None


def _calculate_replacement_reading(
    meter_id: str,
    current_value: Decimal,
    existing: dict,
    line_source_id: str | None = None,
) -> ReadingCalculation:
    last_value = _decimal_from_row(existing.get("last_value"))
    if last_value is None:
        last_value = _get_last_value(meter_id, line_source_id)

    rate = _decimal_from_row(existing.get("rate"))
    if rate is None:
        rate = _get_rate(meter_id)

    produced_unit = current_value - last_value
    amount = produced_unit * rate
    return ReadingCalculation(
        last_value=last_value,
        produced_unit=produced_unit,
        rate=rate,
        amount=amount,
    )


def _decimal_from_row(value) -> Decimal | None:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except InvalidOperation:
        return None


def _iso_week(dt: datetime) -> str:
    """Return ISO week string like '2026-W19'."""
    iso = dt.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def _get_default_rate_setting() -> Decimal:
    values = repositories.get_settings()
    if isinstance(values, dict):
        raw = values.get("default_rate")
        if raw:
            return Decimal(str(raw))
    return Decimal(str(settings.DEFAULT_RATE))


def _now() -> datetime:
    try:
        tz = ZoneInfo(settings.TIMEZONE)
    except ZoneInfoNotFoundError:
        tz = timezone.utc
    return datetime.now(tz)
