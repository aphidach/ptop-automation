from __future__ import annotations

from decimal import Decimal
from typing import Iterable, Sequence
from urllib.parse import urlencode

from linebot.v3.messaging import (
    FlexContainer,
    FlexMessage,
    MessageAction,
    PostbackAction,
    QuickReply,
    QuickReplyItem,
    TextMessage,
)

from app.line.parser import (
    POSTBACK_CANCEL_COLLECTION,
    POSTBACK_CONFIRM_READING,
    POSTBACK_EDIT_READING,
    POSTBACK_FORCE_CONFIRM_READING,
    POSTBACK_RETAKE_PHOTO,
    POSTBACK_LATEST_REPORT,
    POSTBACK_HELP,
    POSTBACK_HISTORY,
    POSTBACK_HISTORY_BATCH_DETAIL,
    POSTBACK_HISTORY_CURRENT,
    POSTBACK_HISTORY_METER,
    POSTBACK_HISTORY_PREVIOUS,
    POSTBACK_SETTINGS,
    POSTBACK_SETTINGS_CANCEL_CHANGE,
    POSTBACK_SETTINGS_CONFIRM_CHANGE,
    POSTBACK_SETTINGS_CONTACT_ADMIN,
    POSTBACK_SETTINGS_EDIT_EXPECTED_COUNT,
    POSTBACK_SETTINGS_EDIT_RATE,
    POSTBACK_SETTINGS_EDIT_REPORT_TITLE,
    POSTBACK_SETTINGS_METER_DETAIL,
    POSTBACK_SETTINGS_METERS,
    POSTBACK_SETTINGS_PERMISSIONS,
    POSTBACK_SETTINGS_RECIPIENTS,
    POSTBACK_SETTINGS_VIEW,
    POSTBACK_SELECT_METER,
    POSTBACK_SKIP_METER,
    POSTBACK_SHOW_STATUS,
    POSTBACK_START_COLLECTION,
)

QUICK_TEXT_LIMIT = 20
DEFAULT_METER_IDS = ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8")


def build_postback_data(action: str, **kwargs: str | int | bool | None) -> str:
    payload = {"action": action}
    for key, value in kwargs.items():
        if value is None:
            continue
        payload[key] = str(value)
    return urlencode(payload)


def _message_action(label: str, text: str) -> MessageAction:
    return MessageAction(label=label[:QUICK_TEXT_LIMIT], text=text[:200])


def _postback_action(label: str, data: str, display_text: str | None = None) -> PostbackAction:
    return PostbackAction(
        label=label[:QUICK_TEXT_LIMIT],
        data=data[:1000],
        display_text=display_text or label,
    )


def _quick_reply_from_actions(items: Sequence[tuple[str, str, str]]) -> QuickReply:
    # (label, action_type, action_payload)
    action_items = []
    for label, action_type, action_payload in items:
        if action_type == "message":
            action = _message_action(label, action_payload)
        else:
            action = _postback_action(label, action_payload)
        action_items.append(QuickReplyItem(action=action))
    return QuickReply(items=action_items)


def _text_with_actions(
    text: str,
    action_items: Iterable[tuple[str, str, str]],
) -> TextMessage:
    return TextMessage(
        text=text,
        quick_reply=_quick_reply_from_actions(list(action_items)),
    )


def build_start_collection_card() -> FlexMessage:
    contents = {
        "type": "bubble",
        "hero": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {"type": "text", "text": "เริ่มบันทึกค่ามิเตอร์สัปดาห์นี้", "weight": "bold", "size": "lg"},
            ],
            "spacing": "xs",
            "paddingAll": "12px",
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {"type": "text", "text": "คุณต้องบันทึกทั้งหมด 8 เครื่อง", "wrap": True},
                {"type": "text", "text": "ระบบจะพาไปทีละเครื่อง M1 ถึง M8", "wrap": True},
            ],
            "paddingAll": "12px",
        },
    }
    return FlexMessage(
        alt_text="เริ่มบันทึกค่ามิเตอร์",
        contents=FlexContainer.from_dict(contents),
    )


def build_meter_request_message(meter_id: str) -> TextMessage:
    meter_actions = [
        (target, "postback", build_postback_data(action=POSTBACK_SELECT_METER, meter_id=target))
        for target in DEFAULT_METER_IDS
    ]
    action = _quick_reply_from_actions(
        [
            ("ข้าม", "postback", build_postback_data(action=POSTBACK_SKIP_METER, meter_id=meter_id)),
            *meter_actions,
            ("ดูสถานะ", "postback", build_postback_data(action=POSTBACK_SHOW_STATUS)),
            ("ยกเลิก", "postback", build_postback_data(action=POSTBACK_CANCEL_COLLECTION)),
        ]
    )
    return TextMessage(
        text=f"กรุณาถ่ายรูปเครื่อง {meter_id}",
        quick_reply=action,
    )

def build_confirmation_card(
    meter_id: str,
    current_value: Decimal,
    prev_value: Decimal,
    produced: Decimal,
    amount: Decimal,
) -> FlexMessage:
    confirm_data = build_postback_data(action=POSTBACK_CONFIRM_READING, meter_id=meter_id)
    edit_data = build_postback_data(action=POSTBACK_EDIT_READING, meter_id=meter_id)
    retake_data = build_postback_data(action=POSTBACK_RETAKE_PHOTO, meter_id=meter_id)
    cancel_data = build_postback_data(action=POSTBACK_CANCEL_COLLECTION)

    contents = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                {"type": "text", "text": "ตรวจพบค่า", "weight": "bold"},
                {"type": "text", "text": meter_id, "size": "xxl", "weight": "bold"},
                {"type": "text", "text": f"ค่าที่อ่านได้: {current_value} kWh"},
                {"type": "text", "text": f"ครั้งก่อน: {prev_value} kWh"},
                {"type": "text", "text": f"ผลิตเพิ่ม: {produced} kWh"},
                {"type": "text", "text": f"รายได้: {amount} บาท"},
                {"type": "text", "text": "ยืนยันค่าหรือไม่?"}
            ],
            "paddingAll": "12px",
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": [
                {
                    "type": "button",
                    "action": {"type": "postback", "label": "ยืนยัน", "data": confirm_data},
                    "style": "primary",
                    "height": "sm",
                },
                {
                    "type": "button",
                    "action": {"type": "postback", "label": "แก้ไข", "data": edit_data},
                    "height": "sm",
                },
                {
                    "type": "button",
                    "action": {"type": "postback", "label": "ถ่ายใหม่", "data": retake_data},
                    "height": "sm",
                },
                {
                    "type": "button",
                    "action": {"type": "postback", "label": "ยกเลิก", "data": cancel_data},
                    "height": "sm",
                },
            ],
            "paddingAll": "12px",
        },
    }
    return FlexMessage(
        alt_text=f"ยืนยันค่ามิเตอร์ {meter_id}",
        contents=FlexContainer.from_dict(contents),
    )


def build_duplicate_warning_card(
    meter_id: str,
    old_value: str,
    new_value: str,
) -> TextMessage:
    return _text_with_actions(
        text=(
            f"รอบนี้มีค่า {meter_id} แล้ว\n"
            f"ค่าเดิม: {old_value} kWh\n"
            f"ค่าใหม่: {new_value} kWh\n"
            "การแทนที่จะเพิ่มในเวอร์ชันถัดไป"
        ),
        action_items=(
            ("ไม่แทนที่", "postback", build_postback_data(action=POSTBACK_CANCEL_COLLECTION)),
            ("ถ่ายใหม่", "postback", build_postback_data(action=POSTBACK_RETAKE_PHOTO, meter_id=meter_id)),
        ),
    )


def build_progress_message(meter_id: str, confirmed_count: int, total_count: int, next_meter: str | None) -> str:
    remain = total_count - confirmed_count
    parts = [
        f"บันทึกค่า {meter_id} เรียบร้อย",
        f"ความคืบหน้า: {confirmed_count}/{total_count} เครื่อง",
        f"เหลืออีก {remain} เครื่อง",
    ]
    if next_meter:
        parts.append(f"ต่อไป: {next_meter}")
    return "\n".join(parts)


def build_unreadable_prompt(meter_id: str) -> TextMessage:
    return _text_with_actions(
        text=f"อ่านตัวเลขจากรูปนี้ไม่ชัดครับ\nกรุณาพิมพ์ค่าเอง เช่น {meter_id} 12508",
        action_items=(
            ("แก้เอง", "message", f"{meter_id} "),
            ("ถ่ายใหม่", "postback", build_postback_data(action=POSTBACK_RETAKE_PHOTO, meter_id=meter_id)),
            ("ยกเลิก", "postback", build_postback_data(action=POSTBACK_CANCEL_COLLECTION)),
        ),
    )


def build_lower_value_warning(meter_id: str, prev_value: Decimal, cur_value: Decimal) -> TextMessage:
    return _text_with_actions(
        text=(
            "ค่าที่อ่านได้ต่ำกว่าครั้งก่อน\n"
            f"ครั้งก่อน: {prev_value} kWh\n"
            f"ครั้งนี้: {cur_value} kWh\n"
            "กรุณาตรวจสอบก่อนบันทึก"
        ),
        action_items=(
            ("ยืนยันว่าใช่", "postback", build_postback_data(action=POSTBACK_FORCE_CONFIRM_READING, meter_id=meter_id)),
            ("แก้ไข", "postback", build_postback_data(action=POSTBACK_EDIT_READING, meter_id=meter_id)),
            ("ถ่ายใหม่", "postback", build_postback_data(action=POSTBACK_RETAKE_PHOTO, meter_id=meter_id)),
        ),
    )


def build_status_card(meter_id: str | None, pending: str, progress_text: str) -> TextMessage:
    lines = ["สถานะปัจจุบัน"]
    if meter_id:
        lines.append(f"มิเตอร์ปัจจุบัน: {meter_id}")
    if pending:
        lines.append(f"รอยืนยัน: {pending}")
    if progress_text:
        lines.append(progress_text)
    return _text_with_actions(
        text="\n".join(lines),
        action_items=(
            ("ดูสรุป", "postback", build_postback_data(action=POSTBACK_START_COLLECTION)),
            ("รายงานล่าสุด", "postback", build_postback_data(action=POSTBACK_LATEST_REPORT)),
            ("ยกเลิก", "postback", build_postback_data(action=POSTBACK_CANCEL_COLLECTION)),
        ),
    )

def build_history_menu_message() -> TextMessage:
    return _text_with_actions(
        text="ประวัติการบันทึกมิเตอร์\n\nเลือกรายการที่ต้องการดูครับ",
        action_items=(
            ("รอบปัจจุบัน", "postback", build_postback_data(action=POSTBACK_HISTORY_CURRENT)),
            ("สัปดาห์ก่อน", "postback", build_postback_data(action=POSTBACK_HISTORY_PREVIOUS)),
            ("เลือกรอบย้อนหลัง", "postback", build_postback_data(action=POSTBACK_HISTORY_PREVIOUS)),
            ("ดูตามมิเตอร์", "postback", build_postback_data(action=POSTBACK_HISTORY_METER)),
            ("รายงานล่าสุด", "postback", build_postback_data(action=POSTBACK_LATEST_REPORT)),
            ("กลับเมนูหลัก", "postback", build_postback_data(action=POSTBACK_HELP)),
        ),
    )

def build_history_empty_message(text: str) -> TextMessage:
    return _text_with_actions(
        text=text,
        action_items=(
            ("เริ่มบันทึกมิเตอร์", "postback", build_postback_data(action=POSTBACK_START_COLLECTION)),
            ("ดูรายงานล่าสุด", "postback", build_postback_data(action=POSTBACK_LATEST_REPORT)),
            ("Help", "postback", build_postback_data(action=POSTBACK_HELP)),
        ),
    )

def build_history_summary_message(title: str, summary) -> TextMessage:
    lines = [
        title,
        "",
        f"รอบ: {summary.week or summary.batch_id}",
        f"สถานะ: {summary.status}",
        f"บันทึกแล้ว: {summary.confirmed_meter_count}/{summary.expected_meter_count} เครื่อง",
    ]
    if summary.missing_meter_ids:
        lines.append(f"ยังขาด: {', '.join(summary.missing_meter_ids)}")
    lines.extend(
        [
            f"รวมผลิต: {_format_number(summary.produced_unit)} kWh",
            f"ยอดเงินรวม: {_format_number(summary.amount)} บาท",
        ]
    )
    return _text_with_actions(
        text="\n".join(lines),
        action_items=(
            (
                "ดูรายละเอียด",
                "postback",
                build_postback_data(action=POSTBACK_HISTORY_BATCH_DETAIL, batch_id=summary.batch_id),
            ),
            ("บันทึกต่อ", "postback", build_postback_data(action=POSTBACK_START_COLLECTION)),
            ("ส่งรายงาน", "postback", build_postback_data(action=POSTBACK_LATEST_REPORT, batch_id=summary.batch_id)),
            ("กลับประวัติ", "postback", build_postback_data(action=POSTBACK_HISTORY)),
        ),
    )

def build_history_detail_message(summary) -> TextMessage:
    lines = [f"รายละเอียดรอบ {summary.week or summary.batch_id}", ""]
    by_meter = {str(row.get("meter_id", "")): row for row in summary.readings}
    for meter_id in DEFAULT_METER_IDS:
        row = by_meter.get(meter_id)
        if not row:
            lines.append(f"{meter_id}: ยังไม่มีข้อมูล")
            continue
        current = _format_number(row.get("current_value", "0"))
        produced = _format_number(row.get("produced_unit", "0"))
        lines.append(f"{meter_id}: {current} kWh (+{produced})")
    return _text_with_actions(
        text="\n".join(lines),
        action_items=(
            ("ส่งรูปรายงาน", "postback", build_postback_data(action=POSTBACK_LATEST_REPORT, batch_id=summary.batch_id)),
            ("ดูตามมิเตอร์", "postback", build_postback_data(action=POSTBACK_HISTORY_METER)),
            ("บันทึกต่อ", "postback", build_postback_data(action=POSTBACK_START_COLLECTION)),
            ("กลับประวัติ", "postback", build_postback_data(action=POSTBACK_HISTORY)),
        ),
    )

def build_history_meter_select_message() -> TextMessage:
    items = [
        (meter_id, "postback", build_postback_data(action=POSTBACK_HISTORY_METER, meter_id=meter_id))
        for meter_id in DEFAULT_METER_IDS
    ]
    items.append(("กลับประวัติ", "postback", build_postback_data(action=POSTBACK_HISTORY)))
    return _text_with_actions(
        text="ต้องการดูประวัติมิเตอร์เครื่องไหนครับ",
        action_items=items,
    )

def build_history_meter_message(meter_id: str, readings: Sequence[dict]) -> TextMessage:
    if not readings:
        return _text_with_actions(
            text=f"ยังไม่มีประวัติของ {meter_id} ครับ",
            action_items=(
                ("เริ่มบันทึกมิเตอร์", "postback", build_postback_data(action=POSTBACK_START_COLLECTION)),
                ("เลือกเครื่องอื่น", "postback", build_postback_data(action=POSTBACK_HISTORY_METER)),
                ("กลับประวัติ", "postback", build_postback_data(action=POSTBACK_HISTORY)),
            ),
        )

    lines = [f"ประวัติ {meter_id}", ""]
    for row in readings:
        week = row.get("week") or row.get("date") or "-"
        current = _format_number(row.get("current_value", "0"))
        produced = _format_number(row.get("produced_unit", "0"))
        lines.append(f"{week}: {current} kWh (+{produced})")
    return _text_with_actions(
        text="\n".join(lines),
        action_items=(
            ("ส่งรายงานล่าสุด", "postback", build_postback_data(action=POSTBACK_LATEST_REPORT)),
            ("เลือกเครื่องอื่น", "postback", build_postback_data(action=POSTBACK_HISTORY_METER)),
            ("กลับประวัติ", "postback", build_postback_data(action=POSTBACK_HISTORY)),
        ),
    )

def build_settings_menu_message(is_admin: bool) -> TextMessage:
    if not is_admin:
        return _text_with_actions(
            text=(
                "ตั้งค่าระบบ\n\n"
                "คุณสามารถดูการตั้งค่าปัจจุบันได้\n"
                "การแก้ไขต้องใช้สิทธิ์ผู้ดูแลระบบ"
            ),
            action_items=(
                ("ดูการตั้งค่าปัจจุบัน", "postback", build_postback_data(action=POSTBACK_SETTINGS_VIEW)),
                ("ดูรายชื่อมิเตอร์", "postback", build_postback_data(action=POSTBACK_SETTINGS_METERS)),
                ("ติดต่อผู้ดูแล", "postback", build_postback_data(action=POSTBACK_SETTINGS_CONTACT_ADMIN)),
                ("Help", "postback", build_postback_data(action=POSTBACK_HELP)),
            ),
        )

    return _text_with_actions(
        text="ตั้งค่าระบบ\n\nเลือกสิ่งที่ต้องการจัดการครับ",
        action_items=(
            ("มิเตอร์ M1-M8", "postback", build_postback_data(action=POSTBACK_SETTINGS_METERS)),
            ("อัตราค่าไฟ", "postback", build_postback_data(action=POSTBACK_SETTINGS_EDIT_RATE)),
            ("จำนวนเครื่อง", "postback", build_postback_data(action=POSTBACK_SETTINGS_EDIT_EXPECTED_COUNT)),
            ("ชื่อรายงาน", "postback", build_postback_data(action=POSTBACK_SETTINGS_EDIT_REPORT_TITLE)),
            ("ผู้รับรายงาน", "postback", build_postback_data(action=POSTBACK_SETTINGS_RECIPIENTS)),
            ("สิทธิ์ผู้ใช้งาน", "postback", build_postback_data(action=POSTBACK_SETTINGS_PERMISSIONS)),
        ),
    )

def build_settings_view_message(values: dict[str, str], is_admin: bool) -> TextMessage:
    lines = [
        "การตั้งค่าปัจจุบัน",
        "",
        f"จำนวนมิเตอร์: {values.get('expected_meter_count', '8')} เครื่อง",
        "รอบบันทึก: รายสัปดาห์",
        f"อัตราเริ่มต้น: {values.get('default_rate', '4.2')} บาท/kWh",
        f"Timezone: {values.get('timezone', 'Asia/Bangkok')}",
        f"ชื่อรายงาน: {values.get('report_title', 'Solar Weekly Report')}",
    ]
    actions = (
        (
            ("แก้อัตราค่าไฟ", "postback", build_postback_data(action=POSTBACK_SETTINGS_EDIT_RATE)),
            ("แก้ชื่อรายงาน", "postback", build_postback_data(action=POSTBACK_SETTINGS_EDIT_REPORT_TITLE)),
            ("แก้จำนวนเครื่อง", "postback", build_postback_data(action=POSTBACK_SETTINGS_EDIT_EXPECTED_COUNT)),
            ("กลับตั้งค่า", "postback", build_postback_data(action=POSTBACK_SETTINGS)),
        )
        if is_admin
        else (
            ("ดูรายชื่อมิเตอร์", "postback", build_postback_data(action=POSTBACK_SETTINGS_METERS)),
            ("ติดต่อผู้ดูแล", "postback", build_postback_data(action=POSTBACK_SETTINGS_CONTACT_ADMIN)),
            ("กลับเมนูหลัก", "postback", build_postback_data(action=POSTBACK_HELP)),
        )
    )
    return _text_with_actions(text="\n".join(lines), action_items=actions)

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

def _format_number(value) -> str:
    try:
        number = Decimal(str(value or "0").replace(",", ""))
    except Exception:
        return str(value)
    if number == number.to_integral():
        return f"{int(number):,}"
    return f"{number:,.2f}".rstrip("0").rstrip(".")

def _bool_th(value: str) -> str:
    return "เปิด" if value.strip().lower() in {"1", "true", "yes", "on"} else "ปิด"
