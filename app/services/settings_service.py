from __future__ import annotations

from decimal import Decimal, InvalidOperation

from app.config import settings
from app.services.audit_service import log_event
from app.sheets import repositories

EVENT_SETTING_CHANGED = "setting_changed"

SETTING_DEFAULT_RATE = "default_rate"
SETTING_EXPECTED_METER_COUNT = "expected_meter_count"
SETTING_REPORT_TITLE = "report_title"
SETTING_TIMEZONE = "timezone"
SETTING_AUTO_SEND_REPORT = "auto_send_report"
SETTING_REPORT_RECIPIENT_IDS = "report_recipient_ids"


def is_admin(source_id: str) -> bool:
    return source_id in set(settings.ADMIN_LINE_USER_IDS + settings.OWNER_LINE_USER_IDS)


def get_current_settings() -> dict[str, str]:
    sheet_values = repositories.get_settings()
    return {
        SETTING_EXPECTED_METER_COUNT: sheet_values.get(
            SETTING_EXPECTED_METER_COUNT, str(settings.EXPECTED_METER_COUNT)
        ),
        SETTING_DEFAULT_RATE: sheet_values.get(SETTING_DEFAULT_RATE, str(settings.DEFAULT_RATE)),
        SETTING_TIMEZONE: sheet_values.get(SETTING_TIMEZONE, settings.TIMEZONE),
        SETTING_REPORT_TITLE: sheet_values.get(SETTING_REPORT_TITLE, "Solar Weekly Report"),
        SETTING_AUTO_SEND_REPORT: sheet_values.get(SETTING_AUTO_SEND_REPORT, "true"),
        SETTING_REPORT_RECIPIENT_IDS: sheet_values.get(SETTING_REPORT_RECIPIENT_IDS, ""),
    }


def get_meter_settings() -> list[dict]:
    return repositories.get_active_meters()


def get_meter_detail(meter_id: str) -> dict | None:
    return repositories.get_meter_by_id(meter_id)


def validate_setting_input(key: str, value: str) -> tuple[bool, str]:
    text = value.strip()
    if key == SETTING_DEFAULT_RATE:
        try:
            if Decimal(text) <= 0:
                return False, "กรุณาพิมพ์ตัวเลข เช่น 4.5"
        except (InvalidOperation, ValueError):
            return False, "กรุณาพิมพ์ตัวเลข เช่น 4.5"
    elif key == SETTING_EXPECTED_METER_COUNT:
        if not text.isdigit() or int(text) <= 0:
            return False, "กรุณาพิมพ์จำนวนเครื่องเป็นตัวเลข เช่น 8"
    elif key == SETTING_REPORT_TITLE and not text:
        return False, "กรุณาพิมพ์ชื่อรายงานใหม่"
    return True, text


def setting_label(key: str) -> str:
    labels = {
        SETTING_DEFAULT_RATE: "อัตราค่าไฟ",
        SETTING_EXPECTED_METER_COUNT: "จำนวนเครื่องต่อรอบ",
        SETTING_REPORT_TITLE: "ชื่อรายงาน",
    }
    return labels.get(key, key)


def setting_impact(key: str) -> str:
    impacts = {
        SETTING_DEFAULT_RATE: "ค่านี้จะใช้กับการบันทึกครั้งถัดไป",
        SETTING_EXPECTED_METER_COUNT: "ค่านี้จะใช้กับรอบบันทึกใหม่หลังจากนี้",
        SETTING_REPORT_TITLE: "ค่านี้จะใช้กับรูปรายงานที่สร้างครั้งถัดไป",
    }
    return impacts.get(key, "ค่านี้จะใช้กับการทำงานครั้งถัดไป")


def apply_setting_change(source_id: str, key: str, old_value: str, new_value: str) -> None:
    repositories.update_setting(key, new_value)
    log_event(
        EVENT_SETTING_CHANGED,
        source_id,
        "",
        {"key": key, "old_value": old_value, "new_value": new_value},
    )
