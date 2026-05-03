from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.line.parser import ParsedReportImport, parse_report_import_text
from app.report.generator import generate_report_image
from app.services.session_service import PendingReportImport
from app.sheets import repositories

logger = logging.getLogger(__name__)


CONFIRMATION_METHOD = "manual_report_import"
NUMERIC_READING_FIELDS = ("current_value", "last_value", "produced_unit", "rate", "amount")


@dataclass
class ReportImportResult:
    success: bool
    batch_id: str
    week: str
    duplicate: bool = False
    report_image_path: str | None = None
    message: str = ""


def build_report_import_preview(
    line_source_id: str,
    raw_text: str,
    image_message_id: str = "",
) -> PendingReportImport:
    parsed = parse_report_import_text(raw_text)
    batch_id = f"{parsed.week}-{line_source_id}" if parsed.week else ""
    errors = list(parsed.errors)
    duplicate = False

    if batch_id and repositories.get_readings_by_batch(batch_id):
        duplicate = True
        errors.append(f"รอบ {batch_id} มีข้อมูลอยู่แล้ว ไม่สามารถนำเข้าซ้ำได้")

    return PendingReportImport(
        batch_id=batch_id,
        week=parsed.week or "",
        date=parsed.report_date.isoformat() if parsed.report_date else "",
        rows=_rows_to_dicts(parsed),
        total_produced_unit=parsed.total_produced_unit,
        total_amount=parsed.total_amount,
        warnings=list(parsed.warnings),
        errors=errors,
        duplicate=duplicate,
        ocr_raw_text=raw_text[:200],
        image_message_id=image_message_id,
    )


def can_confirm_import(pending: PendingReportImport | None) -> bool:
    return bool(
        pending
        and pending.batch_id
        and pending.week
        and len(pending.rows) == 8
        and not pending.errors
        and not pending.duplicate
    )


def confirm_report_import(
    line_source_id: str,
    pending: PendingReportImport,
    line_user_id: str = "",
) -> ReportImportResult:
    if not can_confirm_import(pending):
        return ReportImportResult(
            success=False,
            batch_id=pending.batch_id,
            week=pending.week,
            duplicate=pending.duplicate,
            message="ข้อมูลรายงานยังไม่พร้อมนำเข้าครับ",
        )

    pending_by_meter = {row["meter_id"]: row for row in pending.rows}
    existing_readings = repositories.get_readings_by_batch(pending.batch_id)
    batch = repositories.get_batch_by_id(pending.batch_id)
    if str((batch or {}).get("status", "")).strip().lower() == "complete":
        return ReportImportResult(
            success=False,
            batch_id=pending.batch_id,
            week=pending.week,
            duplicate=True,
            message=f"รอบ {pending.week} มีข้อมูลอยู่แล้ว จึงไม่นำเข้าซ้ำครับ",
        )
    if existing_readings:
        existing_state = _classify_existing_readings(existing_readings, pending_by_meter, line_source_id)
        if existing_state != "partial":
            return ReportImportResult(
                success=False,
                batch_id=pending.batch_id,
                week=pending.week,
                duplicate=True,
                message=f"รอบ {pending.week} มีข้อมูลอยู่แล้ว จึงไม่นำเข้าซ้ำครับ",
            )

    existing_meter_ids = {str(row.get("meter_id", "")) for row in existing_readings}
    rows_to_append = [row for row in pending.rows if row["meter_id"] not in existing_meter_ids]
    now = datetime.now(timezone.utc)
    if not batch:
        repositories.append_batch(_build_batch(pending, line_source_id, now))

    for row in rows_to_append:
        repositories.append_reading(
            _build_reading(
                pending=pending,
                row=row,
                line_source_id=line_source_id,
                line_user_id=line_user_id,
                created_at=now,
            )
        )

    repositories.update_batch_confirmed_count(pending.batch_id, len(pending.rows))
    repositories.update_batch_status(pending.batch_id, "complete")
    report_image_path = generate_report_image(pending.batch_id)
    logger.info("Imported report batch %s with %d readings", pending.batch_id, len(pending.rows))

    return ReportImportResult(
        success=True,
        batch_id=pending.batch_id,
        week=pending.week,
        report_image_path=report_image_path,
        message=f"นำเข้ารายงาน {pending.week} สำเร็จ {len(pending.rows)}/8 เครื่อง",
    )

def _classify_existing_readings(
    existing_readings: list[dict],
    pending_by_meter: dict[str, dict[str, str]],
    line_source_id: str,
) -> str:
    if not existing_readings:
        return "empty"

    seen_meters: set[str] = set()
    for existing in existing_readings:
        meter_id = str(existing.get("meter_id", ""))
        pending_row = pending_by_meter.get(meter_id)
        if not pending_row or meter_id in seen_meters:
            return "conflict"
        if not _matches_pending_import_row(existing, pending_row, line_source_id):
            return "conflict"
        seen_meters.add(meter_id)

    if seen_meters == set(pending_by_meter):
        return "complete"
    return "partial"

def _matches_pending_import_row(
    existing: dict,
    pending_row: dict[str, str],
    line_source_id: str,
) -> bool:
    if str(existing.get("line_source_id", "")) != line_source_id:
        return False
    if str(existing.get("confirmation_method", "")) != CONFIRMATION_METHOD:
        return False
    for field in NUMERIC_READING_FIELDS:
        if not _decimal_equal(existing.get(field), pending_row.get(field)):
            return False
    return True

def _decimal_equal(left, right) -> bool:
    try:
        return Decimal(str(left)) == Decimal(str(right))
    except Exception:
        return False


def _rows_to_dicts(parsed: ParsedReportImport) -> list[dict[str, str]]:
    return [
        {
            "meter_id": row.meter_id,
            "current_value": str(row.current_value),
            "last_value": str(row.last_value),
            "produced_unit": str(row.produced_unit),
            "rate": str(row.rate),
            "amount": str(row.amount),
        }
        for row in parsed.rows
    ]


def _build_batch(
    pending: PendingReportImport,
    line_source_id: str,
    now: datetime,
) -> dict[str, str]:
    return {
        "batch_id": pending.batch_id,
        "week": pending.week,
        "date": pending.date,
        "line_source_id": line_source_id,
        "expected_meter_count": "8",
        "confirmed_meter_count": str(len(pending.rows)),
        "status": "complete",
        "report_image_url": "",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }


def _build_reading(
    pending: PendingReportImport,
    row: dict[str, str],
    line_source_id: str,
    line_user_id: str,
    created_at: datetime,
) -> dict[str, str]:
    meter_id = row["meter_id"]
    return {
        "reading_id": f"rdg_import_{pending.date.replace('-', '')}_{meter_id}",
        "batch_id": pending.batch_id,
        "date": pending.date,
        "week": pending.week,
        "line_source_id": line_source_id,
        "line_user_id": line_user_id,
        "meter_id": meter_id,
        "current_value": row["current_value"],
        "last_value": row["last_value"],
        "produced_unit": row["produced_unit"],
        "rate": row["rate"],
        "amount": row["amount"],
        "ocr_raw_text": pending.ocr_raw_text,
        "ocr_value": row["current_value"],
        "confirmation_method": CONFIRMATION_METHOD,
        "image_message_id": pending.image_message_id,
        "image_file_id": "",
        "created_at": created_at.isoformat(),
    }
