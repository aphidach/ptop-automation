from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Sequence

from linebot.v3.messaging import FlexContainer, FlexMessage, TextMessage

from app.line.parser import (
    POSTBACK_CANCEL_COLLECTION,
    POSTBACK_CONFIRM_READING,
    POSTBACK_EDIT_READING,
    POSTBACK_FORCE_CONFIRM_READING,
    POSTBACK_RETAKE_PHOTO,
    POSTBACK_LATEST_REPORT,
    POSTBACK_HELP,
    POSTBACK_HISTORY,
    POSTBACK_HISTORY_BATCH,
    POSTBACK_HISTORY_BATCH_DETAIL,
    POSTBACK_HISTORY_CURRENT,
    POSTBACK_HISTORY_METER,
    POSTBACK_HISTORY_PREVIOUS,
    POSTBACK_HISTORY_SELECT_WEEK,
    POSTBACK_SETTINGS,
    POSTBACK_SETTINGS_CANCEL_CHANGE,
    POSTBACK_SETTINGS_CONFIRM_CHANGE,
    POSTBACK_SETTINGS_CONTACT_ADMIN,
    POSTBACK_SETTINGS_EDIT_EXPECTED_COUNT,
    POSTBACK_SETTINGS_EDIT_RATE,
    POSTBACK_SETTINGS_EDIT_REPORT_TITLE,
    POSTBACK_CANCEL_IMPORT_REPORT,
    POSTBACK_CONFIRM_IMPORT_REPORT,
    POSTBACK_HELP_FLOW,
    POSTBACK_SETTINGS_IMPORT_REPORT,
    POSTBACK_SETTINGS_METER_DETAIL,
    POSTBACK_SETTINGS_METERS,
    POSTBACK_SETTINGS_PERMISSIONS,
    POSTBACK_SETTINGS_RECIPIENTS,
    POSTBACK_SETTINGS_SYNC_SHEETS,
    POSTBACK_SETTINGS_VIEW,
    POSTBACK_SELECT_METER,
    POSTBACK_SKIP_METER,
    POSTBACK_SHOW_STATUS,
    POSTBACK_START_COLLECTION,
)

from app.line.message_builders.common import (
    CARD_COLORS,
    CARD_PADDING,
    DEFAULT_METER_IDS,
    LINE_QUICK_REPLY_ITEM_LIMIT,
    QUICK_TEXT_LIMIT,
    _body_text,
    _bool_th,
    _card_shell,
    _format_number,
    _kwh_display_value,
    _message_button,
    _message_decimal,
    _meter_grid,
    _metric_row,
    _optional_metric_rows,
    _parse_line_datetime,
    _postback_button,
    _postback_menu_row,
    _quick_reply_from_actions,
    _safe_int,
    _section_title,
    _signed_kwh,
    _status_badge,
    _text_with_actions,
    _thai_date,
    _thai_datetime,
    build_postback_data,
)

def _settings_icon_box(
    icon: str,
    *,
    background_color: str = CARD_COLORS["light_green"],
    color: str = CARD_COLORS["dark_green"],
) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "width": "44px",
        "height": "44px",
        "cornerRadius": "10px",
        "backgroundColor": background_color,
        "justifyContent": "center",
        "contents": [
            {
                "type": "text",
                "text": icon,
                "size": "xl",
                "weight": "bold",
                "color": color,
                "align": "center",
            }
        ],
    }


def _settings_table_row(icon: str, label: str, value: str, *, show_icon: bool = True) -> dict:
    contents = []
    if show_icon:
        contents.append(
            {
                "type": "text",
                "text": icon,
                "size": "xl",
                "weight": "bold",
                "color": CARD_COLORS["dark_green"],
                "align": "center",
                "flex": 1,
            }
        )
    contents.extend(
        [
            {
                "type": "text",
                "text": label,
                "size": "sm",
                "weight": "bold",
                "color": CARD_COLORS["text"],
                "wrap": True,
                "flex": 5 if show_icon else 4,
            },
            {
                "type": "text",
                "text": value,
                "size": "sm",
                "color": CARD_COLORS["dark_green"],
                "align": "end",
                "wrap": True,
                "flex": 5,
                "maxLines": 2,
            },
        ]
    )
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "alignItems": "center",
        "paddingAll": "10px",
        "contents": contents,
    }


def _settings_table(rows: Sequence[tuple[str, str, str]], *, show_icons: bool = True) -> dict:
    contents = []
    for index, (icon, label, value) in enumerate(rows):
        if index:
            contents.append({"type": "separator", "color": "#E0E0E0"})
        contents.append(_settings_table_row(icon, label, value, show_icon=show_icons))
    return {
        "type": "box",
        "layout": "vertical",
        "cornerRadius": "8px",
        "borderWidth": "1px",
        "borderColor": "#E0E0E0",
        "backgroundColor": CARD_COLORS["white"],
        "contents": contents,
    }


def _settings_current_rows(values: dict[str, str]) -> tuple[tuple[str, str, str], ...]:
    expected_meter_count = values.get("expected_meter_count", "8")
    return (
        ("#", "จำนวนมิเตอร์", f"{expected_meter_count} เครื่อง"),
        ("▦", "รอบบันทึก", "รายสัปดาห์"),
        ("⚡", "อัตราไฟฟ้าเริ่มต้น", _settings_rate_display(values.get("default_rate", "4.2"))),
        ("◎", "Timezone", values.get("timezone", "Asia/Bangkok")),
        ("▤", "ชื่อรายงาน", values.get("report_title", "Solar Weekly Report")),
    )


def _settings_primary_action_row() -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "md",
        "alignItems": "center",
        "paddingAll": "12px",
        "cornerRadius": "8px",
        "backgroundColor": CARD_COLORS["primary"],
        "action": {
            "type": "postback",
            "label": "ดูค่าปัจจุบันฉบับเต็ม"[:QUICK_TEXT_LIMIT],
            "data": build_postback_data(action=POSTBACK_SETTINGS_VIEW),
            "displayText": "ดูค่าปัจจุบันฉบับเต็ม",
        },
        "contents": [
            _settings_icon_box(
                "⚙",
                background_color=CARD_COLORS["white"],
                color=CARD_COLORS["dark_green"],
            ),
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "flex": 1,
                "contents": [
                    {
                        "type": "text",
                        "text": "ดูค่าปัจจุบันฉบับเต็ม",
                        "size": "md",
                        "weight": "bold",
                        "color": CARD_COLORS["white"],
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": "ดูรายละเอียดการตั้งค่าทั้งหมด >",
                        "size": "xs",
                        "color": CARD_COLORS["white"],
                        "wrap": True,
                    },
                ],
            },
            {
                "type": "text",
                "text": ">",
                "size": "xxl",
                "color": CARD_COLORS["white"],
                "align": "end",
                "flex": 0,
            },
        ],
    }


def _settings_admin_action_row(
    icon: str,
    label: str,
    value: str,
    action: str,
    *,
    icon_color: str = CARD_COLORS["dark_green"],
    display_text: str | None = None,
) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "alignItems": "center",
        "paddingAll": "10px",
        "action": {
            "type": "postback",
            "label": label[:QUICK_TEXT_LIMIT],
            "data": build_postback_data(action=action),
            "displayText": display_text or label,
        },
        "contents": [
            {
                "type": "text",
                "text": icon,
                "size": "xl",
                "weight": "bold",
                "color": icon_color,
                "align": "center",
                "flex": 1,
            },
            {
                "type": "text",
                "text": label,
                "size": "sm",
                "weight": "bold",
                "color": CARD_COLORS["text"],
                "wrap": True,
                "flex": 5,
            },
            {
                "type": "text",
                "text": value,
                "size": "sm",
                "color": "#607D9B",
                "align": "end",
                "wrap": True,
                "flex": 5,
                "maxLines": 2,
            },
            {
                "type": "text",
                "text": ">",
                "size": "lg",
                "color": "#90A4AE",
                "align": "end",
                "flex": 0,
            },
        ],
    }


def _settings_admin_actions_table() -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "cornerRadius": "8px",
        "borderWidth": "1px",
        "borderColor": "#E0E0E0",
        "backgroundColor": CARD_COLORS["white"],
        "contents": [
            _settings_admin_action_row(
                "G",
                "Sync Google Sheet",
                "แทนที่ SQLite",
                POSTBACK_SETTINGS_SYNC_SHEETS,
                icon_color=CARD_COLORS["primary"],
            ),
            {"type": "separator", "color": "#E0E0E0"},
            _settings_admin_action_row(
                "▧",
                "นำเข้ารายงานเก่า",
                "OCR จากรูปรายงาน",
                POSTBACK_SETTINGS_IMPORT_REPORT,
                icon_color="#2B7DE9",
            ),
        ],
    }


def _settings_updated_display(values: dict[str, str]) -> str:
    for key in ("updated_at", "last_updated_at", "last_push_at", "last_pull_at"):
        parsed = _parse_line_datetime(values.get(key))
        if parsed:
            return _thai_datetime(parsed)
    return ""


def _settings_permission_note(is_admin: bool) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "md",
        "alignItems": "center",
        "paddingAll": "12px",
        "cornerRadius": "8px",
        "borderWidth": "1px",
        "borderColor": "#DCEFE2",
        "backgroundColor": "#F1F8F3",
        "contents": [
            _settings_icon_box(
                "🔒",
                background_color=CARD_COLORS["light_green"],
                color=CARD_COLORS["dark_green"],
            ),
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "flex": 1,
                "contents": [
                    {
                        "type": "text",
                        "text": "เมนูสำหรับผู้ดูแลระบบเท่านั้น"
                        if is_admin
                        else "ดูได้เฉพาะข้อมูลปัจจุบัน",
                        "size": "sm",
                        "weight": "bold",
                        "color": CARD_COLORS["text"],
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": "จัดการและตั้งค่าระบบให้เหมาะสมกับการใช้งาน"
                        if is_admin
                        else "การแก้ไขต้องใช้สิทธิ์ผู้ดูแลระบบ",
                        "size": "xs",
                        "color": CARD_COLORS["neutral_gray"],
                        "wrap": True,
                    },
                ],
            },
        ],
    }


def _settings_rate_display(value: str) -> str:
    try:
        rate = Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return f"{value} บาท/kWh"
    return f"{rate:,.2f} บาท/kWh"


def build_settings_menu_message(
    is_admin: bool,
    values: dict[str, str] | None = None,
) -> FlexMessage:
    settings_values = values or {}

    quick_actions = (
        ("ดูค่าปัจจุบัน", "postback", build_postback_data(action=POSTBACK_SETTINGS_VIEW)),
        ("ดูรายชื่อมิเตอร์", "postback", build_postback_data(action=POSTBACK_SETTINGS_METERS)),
        ("ติดต่อผู้ดูแล", "postback", build_postback_data(action=POSTBACK_SETTINGS_CONTACT_ADMIN)),
        ("Help", "postback", build_postback_data(action=POSTBACK_HELP)),
    )
    if is_admin:
        quick_actions = (
            ("แก้อัตราไฟฟ้า", "postback", build_postback_data(action=POSTBACK_SETTINGS_EDIT_RATE)),
            ("แก้ชื่อรายงาน", "postback", build_postback_data(action=POSTBACK_SETTINGS_EDIT_REPORT_TITLE)),
            ("แก้จำนวนมิเตอร์", "postback", build_postback_data(action=POSTBACK_SETTINGS_EDIT_EXPECTED_COUNT)),
            ("ดูรายชื่อมิเตอร์", "postback", build_postback_data(action=POSTBACK_SETTINGS_METERS)),
            ("ผู้รับรายงาน", "postback", build_postback_data(action=POSTBACK_SETTINGS_RECIPIENTS)),
            ("สิทธิ์ผู้ใช้งาน", "postback", build_postback_data(action=POSTBACK_SETTINGS_PERMISSIONS)),
            ("Sync Google Sheet", "postback", build_postback_data(action=POSTBACK_SETTINGS_SYNC_SHEETS)),
            ("นำเข้ารายงานเก่า", "postback", build_postback_data(action=POSTBACK_SETTINGS_IMPORT_REPORT)),
        )

    body_contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "spacing": "md",
            "alignItems": "flex-start",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "none",
                    "contents": [
                        {
                            "type": "text",
                            "text": "การตั้งค่าปัจจุบัน",
                            "weight": "bold",
                            "size": "xl",
                            "color": CARD_COLORS["dark_green"],
                            "wrap": True,
                        },
                        {
                            "type": "text",
                            "text": "ข้อมูลการตั้งค่าระบบ",
                            "size": "sm",
                            "color": CARD_COLORS["neutral_gray"],
                            "wrap": True,
                            "margin": "xs",
                        },
                    ],
                    "flex": 1,
                },
                _settings_icon_box("▤"),
            ],
        },
        _settings_table(_settings_current_rows(settings_values)),
        _settings_primary_action_row(),
    ]
    if is_admin:
        body_contents.append(_settings_admin_actions_table())
    body_contents.append(_settings_permission_note(is_admin))

    contents = {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": CARD_PADDING,
            "contents": body_contents,
        },
    }

    return FlexMessage(
        alt_text="การตั้งค่าปัจจุบัน",
        contents=FlexContainer.from_dict(contents),
        quick_reply=_quick_reply_from_actions(quick_actions),
    )


def build_settings_sync_success_message() -> TextMessage:
    return _text_with_actions(
        text=(
            "ซิงก์ Google Sheet สำเร็จ\n\n"
            "ดึงข้อมูลจาก Google Sheet มาแทนที่ SQLite เรียบร้อยครับ"
        ),
        action_items=(
            ("ดูค่าปัจจุบัน", "postback", build_postback_data(action=POSTBACK_SETTINGS_VIEW)),
            ("กลับตั้งค่า", "postback", build_postback_data(action=POSTBACK_SETTINGS)),
        ),
    )


def build_settings_sync_failed_message(error: str) -> TextMessage:
    detail = (error or "").strip() or "ไม่ทราบสาเหตุ"
    if len(detail) > 200:
        detail = f"{detail[:197]}..."
    return _text_with_actions(
        text=(
            "ซิงก์ Google Sheet ไม่สำเร็จครับ\n\n"
            f"สาเหตุ: {detail}"
        ),
        action_items=(
            ("ลองอีกครั้ง", "postback", build_postback_data(action=POSTBACK_SETTINGS_SYNC_SHEETS)),
            ("กลับตั้งค่า", "postback", build_postback_data(action=POSTBACK_SETTINGS)),
        ),
    )


def build_settings_view_message(values: dict[str, str], is_admin: bool) -> FlexMessage:
    settings_values = values or {}
    actions = (
        (
            ("แก้อัตราไฟฟ้า", "postback", build_postback_data(action=POSTBACK_SETTINGS_EDIT_RATE)),
            ("แก้ชื่อรายงาน", "postback", build_postback_data(action=POSTBACK_SETTINGS_EDIT_REPORT_TITLE)),
            ("แก้จำนวนมิเตอร์", "postback", build_postback_data(action=POSTBACK_SETTINGS_EDIT_EXPECTED_COUNT)),
            ("กลับตั้งค่า", "postback", build_postback_data(action=POSTBACK_SETTINGS)),
        )
        if is_admin
        else (
            ("ดูรายชื่อมิเตอร์", "postback", build_postback_data(action=POSTBACK_SETTINGS_METERS)),
            ("ติดต่อผู้ดูแล", "postback", build_postback_data(action=POSTBACK_SETTINGS_CONTACT_ADMIN)),
            ("กลับเมนูหลัก", "postback", build_postback_data(action=POSTBACK_HELP)),
        )
    )
    body_contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "spacing": "md",
            "alignItems": "flex-start",
            "contents": [
                _settings_icon_box("▤"),
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "none",
                    "contents": [
                        {
                            "type": "text",
                            "text": "ค่าปัจจุบันของระบบ",
                            "weight": "bold",
                            "size": "xl",
                            "color": CARD_COLORS["dark_green"],
                            "wrap": True,
                        },
                        {
                            "type": "text",
                            "text": "ข้อมูลการตั้งค่าล่าสุด",
                            "size": "sm",
                            "color": CARD_COLORS["neutral_gray"],
                            "wrap": True,
                            "margin": "xs",
                        },
                    ],
                    "flex": 1,
                },
            ],
        },
        _settings_table(_settings_current_rows(settings_values), show_icons=False),
    ]
    updated_display = _settings_updated_display(settings_values)
    if updated_display:
        body_contents.append(
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "xs",
                "alignItems": "center",
                "contents": [
                    {
                        "type": "text",
                        "text": "◷",
                        "size": "sm",
                        "color": CARD_COLORS["data_blue"],
                        "flex": 0,
                    },
                    {
                        "type": "text",
                        "text": f"อัปเดตล่าสุด: {updated_display}",
                        "size": "xs",
                        "color": CARD_COLORS["neutral_gray"],
                        "wrap": True,
                    },
                ],
            }
        )

    contents = {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": CARD_PADDING,
            "contents": body_contents,
        },
    }
    return FlexMessage(
        alt_text="ค่าปัจจุบันของระบบ",
        contents=FlexContainer.from_dict(contents),
        quick_reply=_quick_reply_from_actions(actions),
    )


def build_settings_meters_message(meters: Sequence[dict], is_admin: bool) -> TextMessage:
    action_text = "ดูหรือแก้ไข" if is_admin else "ดู"
    lines = ["ตั้งค่ามิเตอร์", "", f"เลือกเครื่องที่ต้องการ{action_text}"]
    if meters:
        lines.append("")
        for meter in meters:
            meter_id = meter.get("meter_id", "")
            name = meter.get("name", "")
            lines.append(f"{meter_id}: {name}".strip())
    items = [
        (
            str(meter.get("meter_id", "")),
            "postback",
            build_postback_data(action=POSTBACK_SETTINGS_METER_DETAIL, meter_id=str(meter.get("meter_id", ""))),
        )
        for meter in meters
        if meter.get("meter_id")
    ]
    items.append(("กลับตั้งค่า", "postback", build_postback_data(action=POSTBACK_SETTINGS)))
    return _text_with_actions(text="\n".join(lines), action_items=items)


def build_settings_meter_detail_message(meter: dict, is_admin: bool) -> TextMessage:
    meter_id = meter.get("meter_id", "")
    lines = [
        f"มิเตอร์ {meter_id}",
        "",
        f"ชื่อ: {meter.get('name', '-')}",
        f"ตำแหน่ง: {meter.get('location', '-')}",
        f"ลำดับรายงาน: {meter.get('sort_order', '-')}",
        f"สถานะ: {meter.get('active', '-')}",
        f"อัตรา: {meter.get('default_rate', '-')} บาท/kWh",
    ]
    return _text_with_actions(
        text="\n".join(lines),
        action_items=(
            ("แก้อัตราระบบ", "postback", build_postback_data(action=POSTBACK_SETTINGS_EDIT_RATE)),
            ("กลับมิเตอร์", "postback", build_postback_data(action=POSTBACK_SETTINGS_METERS)),
            ("กลับตั้งค่า", "postback", build_postback_data(action=POSTBACK_SETTINGS)),
        )
        if is_admin
        else (
            ("กลับมิเตอร์", "postback", build_postback_data(action=POSTBACK_SETTINGS_METERS)),
            ("ติดต่อผู้ดูแล", "postback", build_postback_data(action=POSTBACK_SETTINGS_CONTACT_ADMIN)),
            ("กลับตั้งค่า", "postback", build_postback_data(action=POSTBACK_SETTINGS)),
        ),
    )


def build_settings_edit_prompt_message(key: str, current_value: str) -> TextMessage:
    if key == "default_rate":
        text = (
            "อัตราค่าไฟปัจจุบัน\n\n"
            f"ค่าเริ่มต้น: {current_value} บาท/kWh\n\n"
            "ต้องการแก้เป็นเท่าไหร่ครับ\n"
            "พิมพ์ตัวเลข เช่น 4.5"
        )
    elif key == "expected_meter_count":
        text = (
            "จำนวนเครื่องต่อรอบปัจจุบัน\n\n"
            f"จำนวน: {current_value} เครื่อง\n\n"
            "ต้องการแก้เป็นกี่เครื่องครับ\n"
            "พิมพ์ตัวเลข เช่น 8"
        )
    else:
        text = (
            "ตั้งค่ารายงาน\n\n"
            "ชื่อรายงานปัจจุบัน:\n"
            f"{current_value}\n\n"
            "พิมพ์ชื่อรายงานใหม่ครับ"
        )
    return _text_with_actions(
        text=text,
        action_items=(("ยกเลิก", "postback", build_postback_data(action=POSTBACK_SETTINGS_CANCEL_CHANGE)),),
    )


def build_settings_confirm_change_message(change) -> TextMessage:
    return _text_with_actions(
        text=(
            f"ยืนยันการแก้{change.label}\n\n"
            f"ค่าเดิม: {change.old_value}\n"
            f"ค่าใหม่: {change.new_value}\n\n"
            f"{change.impact}"
        ),
        action_items=(
            (
                "ยืนยัน",
                "postback",
                build_postback_data(action=POSTBACK_SETTINGS_CONFIRM_CHANGE, change_id=change.change_id),
            ),
            (
                "ยกเลิก",
                "postback",
                build_postback_data(action=POSTBACK_SETTINGS_CANCEL_CHANGE, change_id=change.change_id),
            ),
        ),
    )


def build_settings_recipients_message(values: dict[str, str], is_admin: bool) -> TextMessage:
    recipients = [item for item in values.get("report_recipient_ids", "").split(",") if item.strip()]
    text = (
        "ผู้รับรายงาน\n\n"
        f"ส่งอัตโนมัติ: {_bool_th(values.get('auto_send_report', 'true'))}\n"
        "ปลายทางหลัก: LINE group ปัจจุบัน\n"
        f"ผู้รับเพิ่มเติม: {len(recipients)} รายการ"
    )
    return _text_with_actions(
        text=text,
        action_items=(
            ("ดูรายงานล่าสุด", "postback", build_postback_data(action=POSTBACK_LATEST_REPORT)),
            ("กลับตั้งค่า", "postback", build_postback_data(action=POSTBACK_SETTINGS)),
        ),
    )


def build_settings_permissions_message(is_admin: bool) -> TextMessage:
    return _text_with_actions(
        text=(
            "สิทธิ์ผู้ใช้งาน\n\n"
            "ใช้ ADMIN_LINE_USER_IDS และ OWNER_LINE_USER_IDS จาก environment สำหรับ MVP\n"
            "การแก้สิทธิ์ผ่าน LINE จะเพิ่มในเฟส hardening"
        ),
        action_items=(
            ("ดูการตั้งค่า", "postback", build_postback_data(action=POSTBACK_SETTINGS_VIEW)),
            ("กลับตั้งค่า", "postback", build_postback_data(action=POSTBACK_SETTINGS)),
        ),
    )


def build_settings_not_admin_message() -> TextMessage:
    return _text_with_actions(
        text="การแก้ไขต้องใช้สิทธิ์ผู้ดูแลระบบครับ",
        action_items=(
            ("ดูการตั้งค่าปัจจุบัน", "postback", build_postback_data(action=POSTBACK_SETTINGS_VIEW)),
            ("ติดต่อผู้ดูแล", "postback", build_postback_data(action=POSTBACK_SETTINGS_CONTACT_ADMIN)),
            ("Help", "postback", build_postback_data(action=POSTBACK_HELP)),
        ),
    )
