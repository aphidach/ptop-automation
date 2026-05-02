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
