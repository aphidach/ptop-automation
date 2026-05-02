import json
import re
from dataclasses import dataclass
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
POSTBACK_HELP = "help"


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
    field: Optional[str] = None
    change_id: Optional[str] = None
    replace: bool = False
    raw: str = ""


_METER_ONLY = re.compile(r"^([Mm]\d+)$")
_METER_VALUE = re.compile(r"^([Mm]\d+)\s+([0-9][0-9,]*(?:\.\d+)?)$")
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
