import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Optional
from urllib.parse import parse_qs

METER = "meter"
METER_VALUE = "meter_value"
OK = "ok"
STATUS = "status"
HELP = "help"
CANCEL = "cancel"
GEN = "gen"
REPORT = "report"
UNKNOWN = "unknown"
POSTBACK_UNKNOWN = "postback_unknown"
POSTBACK_START_COLLECTION = "start_collection"
POSTBACK_SELECT_METER = "select_meter"
POSTBACK_CONFIRM_READING = "confirm_reading"
POSTBACK_FORCE_CONFIRM_READING = "force_confirm_reading"
POSTBACK_EDIT_READING = "edit_reading"
POSTBACK_RETAKE_PHOTO = "retake_photo"
POSTBACK_SKIP_METER = "skip_meter"
POSTBACK_SHOW_STATUS = "show_status"
POSTBACK_LATEST_REPORT = "latest_report"
POSTBACK_WEEKLY_SUMMARY = "weekly_summary"
POSTBACK_CANCEL_COLLECTION = "cancel_collection"
POSTBACK_REPLACE_READING = "replace_reading"
POSTBACK_HISTORY = "history"
POSTBACK_HISTORY_CURRENT = "history_current"
POSTBACK_HISTORY_PREVIOUS = "history_previous"
POSTBACK_HISTORY_BATCH = "history_batch"
POSTBACK_HISTORY_BATCH_DETAIL = "history_batch_detail"
POSTBACK_HISTORY_METER = "history_meter"
POSTBACK_HISTORY_SELECT_WEEK = "history_select_week"
POSTBACK_SETTINGS = "settings"
POSTBACK_SETTINGS_VIEW = "settings_view"
POSTBACK_SETTINGS_METERS = "settings_meters"
POSTBACK_SETTINGS_METER_DETAIL = "settings_meter_detail"
POSTBACK_SETTINGS_EDIT_METER = "settings_edit_meter"
POSTBACK_SETTINGS_EDIT_RATE = "settings_edit_rate"
POSTBACK_SETTINGS_EDIT_REPORT_TITLE = "settings_edit_report_title"
POSTBACK_SETTINGS_EDIT_EXPECTED_COUNT = "settings_edit_expected_count"
POSTBACK_SETTINGS_RECIPIENTS = "settings_recipients"
POSTBACK_SETTINGS_PERMISSIONS = "settings_permissions"
POSTBACK_SETTINGS_CONFIRM_CHANGE = "settings_confirm_change"
POSTBACK_SETTINGS_CANCEL_CHANGE = "settings_cancel_change"
POSTBACK_SETTINGS_CONTACT_ADMIN = "settings_contact_admin"
POSTBACK_SETTINGS_IMPORT_REPORT = "settings_import_report"
POSTBACK_SETTINGS_SYNC_SHEETS = "settings_sync_sheets"
POSTBACK_CONFIRM_IMPORT_REPORT = "confirm_import_report"
POSTBACK_CANCEL_IMPORT_REPORT = "cancel_import_report"
POSTBACK_HELP = "help"
POSTBACK_HELP_FLOW = "help_flow"

REPORT_IMPORT_EXPECTED_ROWS = 8
REPORT_IMPORT_AMOUNT_TOLERANCE = Decimal("0.1")
REPORT_IMPORT_METER_IDS = ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8")
_THAI_MONTHS = {
    "มกราคม": 1,
    "กุมภาพันธ์": 2,
    "มีนาคม": 3,
    "เมษายน": 4,
    "พฤษภาคม": 5,
    "มิถุนายน": 6,
    "กรกฎาคม": 7,
    "สิงหาคม": 8,
    "กันยายน": 9,
    "ตุลาคม": 10,
    "พฤศจิกายน": 11,
    "ธันวาคม": 12,
}


@dataclass
class ParsedCommand:
    type: str = UNKNOWN
    meter_id: Optional[str] = None
    batch_id: Optional[str] = None
    value: Optional[Decimal] = None
    raw: str = ""


@dataclass
class ParsedPostback:
    type: str = POSTBACK_UNKNOWN
    meter_id: Optional[str] = None
    batch_id: Optional[str] = None
    topic: Optional[str] = None
    field: Optional[str] = None
    change_id: Optional[str] = None
    replace: bool = False
    raw: str = ""

@dataclass
class ParsedReportImportRow:
    meter_id: str
    row_number: int
    current_value: Decimal
    last_value: Decimal
    produced_unit: Decimal
    rate: Decimal
    amount: Decimal

@dataclass
class ParsedReportImport:
    success: bool
    report_date: Optional[date]
    week: Optional[str]
    rows: list[ParsedReportImportRow]
    total_produced_unit: Decimal
    total_amount: Decimal
    reported_total_amount: Optional[Decimal]
    warnings: list[str]
    errors: list[str]
    raw_text: str = ""


_METER_ONLY = re.compile(r"^([Mm]\d+)$")
_METER_VALUE = re.compile(r"^([Mm]\d+)\s+([0-9][0-9,]*(?:\.\d+)?)$")
_NUMBER_TOKEN = re.compile(r"-?\d[\d,]*(?:\.\d+)?")
_REPORT_ROW_START = re.compile(r"^\s*(\d{1,2})\s*[\.)]\s+")
_ISO_DATE = re.compile(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b")
_SLASH_DATE = re.compile(r"\b(\d{1,2})[/-](\d{1,2})[/-](\d{4})\b")
_BOOL_TRUE = {"1", "true", "yes", "on"}


def parse_command(text: str) -> ParsedCommand:
    text = text.strip()
    upper = text.upper()

    if upper == "OK":
        return ParsedCommand(type=OK, raw=text)
    if upper == "STATUS":
        return ParsedCommand(type=STATUS, raw=text)
    if upper == "HELP":
        return ParsedCommand(type=HELP, raw=text)
    if upper == "CANCEL":
        return ParsedCommand(type=CANCEL, raw=text)
    if upper == "GEN":
        return ParsedCommand(type=GEN, raw=text)
    if upper.startswith("GEN "):
        batch_id = text.split(maxsplit=1)[1].strip()
        if batch_id:
            return ParsedCommand(type=GEN, batch_id=batch_id, raw=text)
    if upper == "REPORT":
        return ParsedCommand(type=REPORT, raw=text)
    if upper.startswith("REPORT "):
        batch_id = text.split(maxsplit=1)[1].strip()
        if batch_id:
            return ParsedCommand(type=REPORT, batch_id=batch_id, raw=text)

    m = _METER_VALUE.match(text)
    if m:
        return ParsedCommand(
            type=METER_VALUE,
            meter_id=m.group(1).upper(),
            value=Decimal(m.group(2).replace(",", "")),
            raw=text,
        )

    m = _METER_ONLY.match(text)
    if m:
        return ParsedCommand(type=METER, meter_id=m.group(1).upper(), raw=text)

    return ParsedCommand(type=UNKNOWN, raw=text)


def parse_postback_action(raw: str) -> ParsedPostback:
    raw = (raw or "").strip()
    if not raw:
        return ParsedPostback(type=POSTBACK_UNKNOWN, raw=raw)

    data: dict[str, str] = {}
    if raw.startswith("{") and raw.endswith("}"):
        try:
            payload = json.loads(raw)
        except Exception:
            payload = {}
        if isinstance(payload, dict):
            for key, value in payload.items():
                if isinstance(value, str):
                    data[key.strip()] = value.strip()
                elif value is not None:
                    data[key.strip()] = str(value)

    if not data and "=" in raw:
        parsed = parse_qs(raw, keep_blank_values=True)
        for key, values in parsed.items():
            if values:
                data[key.strip()] = values[0].strip()
    elif not data and ":" in raw:
        action, _, meter_id = raw.partition(":")
        if action:
            data["action"] = action.strip()
            if meter_id:
                data["meter_id"] = meter_id.strip()

    action = data.get("action", "").strip().lower()
    if not action:
        return ParsedPostback(type=POSTBACK_UNKNOWN, raw=raw)

    return ParsedPostback(
        type=action,
        meter_id=_normalize_meter_id(data.get("meter_id")),
        batch_id=(data.get("batch_id") or "").strip() or None,
        topic=(data.get("topic") or "").strip() or None,
        field=(data.get("field") or "").strip() or None,
        change_id=(data.get("change_id") or "").strip() or None,
        replace=_normalize_bool(data.get("replace")),
        raw=raw,
    )


def _normalize_meter_id(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    candidate = value.strip().upper()
    if not re.fullmatch(r"M\d+", candidate):
        return None
    return candidate


def _normalize_bool(value: Optional[str]) -> bool:
    if not value:
        return False
    return value.strip().lower() in _BOOL_TRUE


def is_valid_meter(meter_id: str, valid_ids: list[str]) -> bool:
    return meter_id in valid_ids

def parse_report_import_text(
    raw_text: str,
    meter_ids: tuple[str, ...] = REPORT_IMPORT_METER_IDS,
) -> ParsedReportImport:
    """Parse OCR text from the generated weekly report format."""
    text = raw_text or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    report_date = _parse_report_date(text, lines)
    week = _iso_week(report_date) if report_date else None
    rows = _parse_report_rows(lines, meter_ids)
    reported_total = _parse_reported_total(lines)

    warnings: list[str] = []
    errors: list[str] = []
    if report_date is None:
        errors.append("อ่านวันที่จากรายงานไม่ได้")

    if len(rows) != REPORT_IMPORT_EXPECTED_ROWS:
        errors.append(f"อ่านแถวได้ {len(rows)}/{REPORT_IMPORT_EXPECTED_ROWS} แถว")

    row_counts: dict[int, int] = {}
    for row in rows:
        row_counts[row.row_number] = row_counts.get(row.row_number, 0) + 1
    duplicate_numbers = [str(number) for number, count in sorted(row_counts.items()) if count > 1]
    if duplicate_numbers:
        errors.append(f"พบเลขแถวซ้ำ: {', '.join(duplicate_numbers)}")

    seen = set(row_counts)
    missing_numbers = [str(i) for i in range(1, REPORT_IMPORT_EXPECTED_ROWS + 1) if i not in seen]
    if missing_numbers:
        errors.append(f"ไม่พบแถวที่ {', '.join(missing_numbers)}")

    total_produced = sum((row.produced_unit for row in rows), Decimal("0"))
    total_amount = sum((row.amount for row in rows), Decimal("0"))

    for row in rows:
        expected_produced = row.current_value - row.last_value
        if _decimal_diff(expected_produced, row.produced_unit) > REPORT_IMPORT_AMOUNT_TOLERANCE:
            errors.append(
                f"{row.meter_id}: ผลิตได้ไม่ตรงกับอ่านหลัง-อ่านก่อน "
                f"({row.produced_unit} != {expected_produced})"
            )

        expected_amount = row.produced_unit * row.rate
        if _decimal_diff(expected_amount, row.amount) > REPORT_IMPORT_AMOUNT_TOLERANCE:
            errors.append(
                f"{row.meter_id}: ยอดเงินไม่ตรงกับผลิตได้ x อัตรา "
                f"({row.amount} != {expected_amount})"
            )

    if reported_total is None:
        warnings.append("ไม่พบยอดรวมในรายงาน")
    elif _decimal_diff(total_amount, reported_total) > REPORT_IMPORT_AMOUNT_TOLERANCE:
        errors.append(f"ยอดรวมไม่ตรง ({reported_total} != {total_amount})")

    return ParsedReportImport(
        success=not errors,
        report_date=report_date,
        week=week,
        rows=rows,
        total_produced_unit=total_produced,
        total_amount=total_amount,
        reported_total_amount=reported_total,
        warnings=warnings,
        errors=errors,
        raw_text=text,
    )

def _parse_report_rows(
    lines: list[str],
    meter_ids: tuple[str, ...],
) -> list[ParsedReportImportRow]:
    rows: list[ParsedReportImportRow] = []
    for line in lines:
        row_match = _REPORT_ROW_START.match(line)
        if not row_match:
            continue
        row_number = int(row_match.group(1))
        if row_number < 1 or row_number > len(meter_ids):
            continue
        numbers = [_to_decimal(token) for token in _NUMBER_TOKEN.findall(line)]
        if len(numbers) < 6:
            continue
        current_value, last_value, produced_unit, rate, amount = numbers[-5:]
        rows.append(
            ParsedReportImportRow(
                meter_id=meter_ids[row_number - 1],
                row_number=row_number,
                current_value=current_value,
                last_value=last_value,
                produced_unit=produced_unit,
                rate=rate,
                amount=amount,
            )
        )
    rows.sort(key=lambda row: row.row_number)
    return rows

def _parse_reported_total(lines: list[str]) -> Optional[Decimal]:
    for line in reversed(lines):
        normalized = line.lower()
        if "รวม" not in normalized and "total" not in normalized:
            continue
        numbers = _NUMBER_TOKEN.findall(line)
        if numbers:
            return _to_decimal(numbers[-1])
    return None

def _parse_report_date(text: str, lines: list[str]) -> Optional[date]:
    iso_match = _ISO_DATE.search(text)
    if iso_match:
        return _safe_date(
            int(iso_match.group(1)),
            int(iso_match.group(2)),
            int(iso_match.group(3)),
        )

    slash_match = _SLASH_DATE.search(text)
    if slash_match:
        return _safe_date(
            _normalize_year(int(slash_match.group(3))),
            int(slash_match.group(2)),
            int(slash_match.group(1)),
        )

    for line in lines:
        month = next((value for name, value in _THAI_MONTHS.items() if name in line), None)
        if month is None:
            continue
        numbers = [int(token.replace(",", "")) for token in _NUMBER_TOKEN.findall(line)]
        if len(numbers) < 2:
            continue
        day = numbers[0]
        year = _normalize_year(numbers[-1])
        parsed = _safe_date(year, month, day)
        if parsed:
            return parsed
    return None

def _safe_date(year: int, month: int, day: int) -> Optional[date]:
    try:
        return date(year, month, day)
    except ValueError:
        return None

def _normalize_year(year: int) -> int:
    if year > 2400:
        return year - 543
    return year

def _iso_week(value: date) -> str:
    iso = value.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"

def _to_decimal(value: str) -> Decimal:
    return Decimal(value.replace(",", ""))

def _decimal_diff(left: Decimal, right: Decimal) -> Decimal:
    diff = left - right
    return diff.copy_abs()
