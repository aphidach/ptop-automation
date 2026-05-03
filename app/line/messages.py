from __future__ import annotations

import os
from decimal import Decimal
from typing import Iterable, Sequence
from urllib.parse import urlencode, urlparse

from linebot.v3.messaging import (
    FlexContainer,
    FlexMessage,
    ImageMessage,
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
    POSTBACK_SETTINGS_VIEW,
    POSTBACK_SELECT_METER,
    POSTBACK_SKIP_METER,
    POSTBACK_SHOW_STATUS,
    POSTBACK_START_COLLECTION,
)

QUICK_TEXT_LIMIT = 20
DEFAULT_METER_IDS = ("M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8")

CARD_COLORS = {
    "primary": "#4CAF50",
    "dark_green": "#2E7D32",
    "light_green": "#E8F5E9",
    "energy_yellow": "#FFC107",
    "warning_text": "#8A5A00",
    "data_blue": "#64B5F6",
    "neutral_gray": "#9E9E9E",
    "page_background": "#F5F7F5",
    "white": "#FFFFFF",
    "text": "#1F2933",
}
CARD_PADDING = "16px"

HELP_TOPIC_START_COLLECTION = "start_collection"
HELP_TOPIC_CONFIRM_READING = "confirm_reading"
HELP_TOPIC_STATUS = "status"
HELP_TOPIC_LATEST_REPORT = "latest_report"
HELP_TOPIC_HISTORY = "history"
HELP_TOPIC_SETTINGS = "settings"
HELP_TOPIC_SETTINGS_ADMIN = "settings_admin"
HELP_TOPIC_IMPORT_REPORT = "import_report"
HELP_TOPIC_TROUBLESHOOTING = "troubleshooting"
HELP_TOPIC_TEXT_COMMANDS = "text_commands"
HELP_TOPIC_CONTACT_ADMIN = "contact_admin"

HELP_FLOW_IMAGE_ASSETS = {
    HELP_TOPIC_START_COLLECTION: "start-collection-board-ai.png",
    HELP_TOPIC_CONFIRM_READING: "confirm-reading-board-ai.png",
    HELP_TOPIC_LATEST_REPORT: "latest-report-board-ai.png",
    HELP_TOPIC_HISTORY: "history-board-ai.png",
    HELP_TOPIC_SETTINGS: "settings-board-ai.png",
    HELP_TOPIC_SETTINGS_ADMIN: "settings-admin-board-ai.png",
    HELP_TOPIC_IMPORT_REPORT: "import-report-board-ai.png",
    HELP_TOPIC_TROUBLESHOOTING: "troubleshooting-board-ai.png",
    HELP_TOPIC_TEXT_COMMANDS: "text-commands-board-ai.png",
}

HELP_FLOW_PREVIEW_IMAGE_ASSETS = {
    HELP_TOPIC_START_COLLECTION: "start-collection-board-ai-preview.jpg",
    HELP_TOPIC_CONFIRM_READING: "confirm-reading-board-ai-preview.jpg",
    HELP_TOPIC_LATEST_REPORT: "latest-report-board-ai-preview.jpg",
    HELP_TOPIC_HISTORY: "history-board-ai-preview.jpg",
    HELP_TOPIC_SETTINGS: "settings-board-ai-preview.jpg",
    HELP_TOPIC_SETTINGS_ADMIN: "settings-admin-board-ai-preview.jpg",
    HELP_TOPIC_IMPORT_REPORT: "import-report-board-ai-preview.jpg",
    HELP_TOPIC_TROUBLESHOOTING: "troubleshooting-board-ai-preview.jpg",
    HELP_TOPIC_TEXT_COMMANDS: "text-commands-board-ai-preview.jpg",
}

HELP_FLOW_TOPICS = {
    HELP_TOPIC_START_COLLECTION: {
        "label": "บันทึกมิเตอร์",
        "title": "วิธีเริ่มบันทึกค่ามิเตอร์",
        "text": (
            "วิธีเริ่มบันทึกค่ามิเตอร์\n"
            "1) กดเมนู บันทึกมิเตอร์\n"
            "2) ระบบเปิดรอบสัปดาห์และบอกเครื่องถัดไป เช่น M1\n"
            "3) ถ่ายรูปมิเตอร์ให้ชัด แล้วตรวจค่า OCR\n"
            "4) ทำต่อจนครบ M1 ถึง M8 ระบบจะสร้างรายงานให้อัตโนมัติ"
        ),
    },
    HELP_TOPIC_CONFIRM_READING: {
        "label": "ยืนยัน/แก้ OCR",
        "title": "วิธียืนยันหรือแก้ค่า OCR",
        "text": (
            "วิธียืนยันหรือแก้ค่า OCR\n"
            "ตรวจเครื่องและค่าที่ระบบอ่านได้ก่อนกดยืนยัน\n"
            "ถ้าผิด ให้กด แก้ไข แล้วพิมพ์ เช่น M1 12508\n"
            "ถ้ารูปไม่ชัด ให้กด ถ่ายใหม่"
        ),
    },
    HELP_TOPIC_STATUS: {
        "label": "ดูสถานะ",
        "title": "วิธีดูสถานะรอบบันทึก",
        "text": (
            "วิธีดูสถานะ\n"
            "กด ดูสถานะ หรือพิมพ์ STATUS เพื่อดูเครื่องปัจจุบัน "
            "ค่าที่รอยืนยัน ความคืบหน้า และรายการที่ยังขาด"
        ),
    },
    HELP_TOPIC_LATEST_REPORT: {
        "label": "รายงานล่าสุด",
        "title": "วิธีดูรายงานล่าสุด",
        "text": (
            "วิธีดูรายงานล่าสุด\n"
            "กดเมนู รายงานล่าสุด ระบบจะค้นหารอบล่าสุดที่มีรายงานแล้วส่งรูปกลับใน LINE\n"
            "ถ้ายังไม่มีรายงาน ให้เริ่มบันทึกมิเตอร์ก่อน"
        ),
    },
    HELP_TOPIC_HISTORY: {
        "label": "ประวัติ",
        "title": "วิธีดูประวัติ",
        "text": (
            "วิธีดูประวัติ\n"
            "กดเมนู ประวัติ แล้วเลือกรอบปัจจุบัน สัปดาห์ก่อน "
            "รอบย้อนหลัง หรือดูตามมิเตอร์"
        ),
    },
    HELP_TOPIC_SETTINGS: {
        "label": "ตั้งค่า",
        "title": "วิธีดูการตั้งค่า",
        "text": (
            "วิธีดูการตั้งค่า\n"
            "กดเมนู ตั้งค่า เพื่อดูค่าปัจจุบันและรายชื่อมิเตอร์\n"
            "การแก้ไขต้องใช้สิทธิ์ admin"
        ),
    },
    HELP_TOPIC_SETTINGS_ADMIN: {
        "label": "ตั้งค่าแอดมิน",
        "title": "วิธีจัดการการตั้งค่า",
        "text": (
            "วิธีจัดการการตั้งค่า\n"
            "Admin กด ตั้งค่า เพื่อแก้ rate จำนวนเครื่อง ชื่อรายงาน "
            "ผู้รับรายงาน และสิทธิ์ผู้ใช้งาน"
        ),
    },
    HELP_TOPIC_IMPORT_REPORT: {
        "label": "นำเข้ารายงานเก่า",
        "title": "วิธีนำเข้ารายงานเก่า",
        "text": (
            "วิธีนำเข้ารายงานเก่า\n"
            "Admin กด ตั้งค่า > นำเข้ารายงานเก่า แล้วส่งรูปรายงานเก่า\n"
            "ระบบจะอ่านตารางและให้ตรวจสอบก่อนบันทึก"
        ),
    },
    HELP_TOPIC_TROUBLESHOOTING: {
        "label": "แก้ปัญหา",
        "title": "วิธีแก้ปัญหาที่พบบ่อย",
        "text": (
            "วิธีแก้ปัญหาที่พบบ่อย\n"
            "ถ้า OCR ไม่ชัด ให้กด ถ่ายใหม่\n"
            "ถ้าค่าผิด ให้กด แก้ไข แล้วพิมพ์ค่าเอง\n"
            "ถ้าค่าต่ำกว่าเดิม ตรวจสอบมิเตอร์ก่อนยืนยัน"
        ),
    },
    HELP_TOPIC_TEXT_COMMANDS: {
        "label": "คำสั่งพิมพ์เอง",
        "title": "คำสั่งพิมพ์เอง",
        "text": (
            "คำสั่งพิมพ์เอง\n"
            "M1 ถึง M8 — เลือกมิเตอร์\n"
            "M1 12508 — กรอกค่าเองหรือแก้ OCR\n"
            "OK — ยืนยันค่าล่าสุด\n"
            "STATUS — ดูสถานะ\n"
            "REPORT [รอบ] — ส่งรายงาน\n"
            "HELP — ดูคำสั่ง\n"
            "CANCEL — ยกเลิก pending confirmation"
        ),
    },
    HELP_TOPIC_CONTACT_ADMIN: {
        "label": "ติดต่อแอดมิน",
        "title": "ติดต่อผู้ดูแลระบบ",
        "text": (
            "ติดต่อผู้ดูแลระบบ\n"
            "แจ้งผู้ดูแลใน LINE group นี้ หากต้องการแก้การตั้งค่า "
            "สิทธิ์ผู้ใช้งาน หรือเพิ่ม admin"
        ),
    },
}

HELP_MENU_TOPICS = (
    HELP_TOPIC_START_COLLECTION,
    HELP_TOPIC_CONFIRM_READING,
    HELP_TOPIC_STATUS,
    HELP_TOPIC_LATEST_REPORT,
    HELP_TOPIC_HISTORY,
    HELP_TOPIC_SETTINGS,
    HELP_TOPIC_SETTINGS_ADMIN,
    HELP_TOPIC_IMPORT_REPORT,
    HELP_TOPIC_TROUBLESHOOTING,
    HELP_TOPIC_TEXT_COMMANDS,
    HELP_TOPIC_CONTACT_ADMIN,
)


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


def _postback_button(
    label: str,
    action: str,
    *,
    style: str = "secondary",
    color: str | None = None,
    height: str = "sm",
    display_text: str | None = None,
    **kwargs: str | int | bool | None,
) -> dict:
    button = {
        "type": "button",
        "style": style,
        "height": height,
        "action": {
            "type": "postback",
            "label": label[:QUICK_TEXT_LIMIT],
            "data": build_postback_data(action=action, **kwargs),
            "displayText": display_text or label,
        },
    }
    if color:
        button["color"] = color
    return button


def _section_title(text: str, *, color: str = CARD_COLORS["dark_green"]) -> dict:
    return {
        "type": "text",
        "text": text,
        "weight": "bold",
        "size": "sm",
        "color": color,
        "wrap": True,
    }


def _status_badge(label: str, *, color: str, background_color: str) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "cornerRadius": "12px",
        "paddingAll": "6px",
        "backgroundColor": background_color,
        "contents": [
            {
                "type": "text",
                "text": label,
                "size": "xs",
                "weight": "bold",
                "align": "center",
                "color": color,
                "wrap": True,
            }
        ],
    }


def _metric_row(label: str, value: str, *, color: str = CARD_COLORS["text"]) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "md",
        "contents": [
            {
                "type": "text",
                "text": label,
                "size": "sm",
                "color": CARD_COLORS["neutral_gray"],
                "flex": 4,
                "wrap": True,
            },
            {
                "type": "text",
                "text": value,
                "size": "sm",
                "weight": "bold",
                "color": color,
                "align": "end",
                "flex": 5,
                "wrap": True,
            },
        ],
    }


def _meter_grid(
    *,
    current_meter_id: str | None = None,
    missing_meter_ids: Sequence[str] | None = None,
    confirmed_meter_count: int | None = None,
    total_count: int | None = None,
) -> dict:
    missing = set(missing_meter_ids or ())
    meter_boxes = []
    for meter_id in DEFAULT_METER_IDS:
        is_current = meter_id == current_meter_id
        is_missing = meter_id in missing if missing_meter_ids is not None else False
        if is_current:
            background = CARD_COLORS["data_blue"]
            text_color = CARD_COLORS["white"]
        elif missing_meter_ids is None:
            background = CARD_COLORS["page_background"]
            text_color = CARD_COLORS["text"]
        elif is_missing:
            background = "#FFF8E1"
            text_color = CARD_COLORS["warning_text"]
        else:
            background = CARD_COLORS["light_green"]
            text_color = CARD_COLORS["dark_green"]
        meter_boxes.append(
            {
                "type": "box",
                "layout": "vertical",
                "cornerRadius": "8px",
                "paddingAll": "6px",
                "backgroundColor": background,
                "contents": [
                    {
                        "type": "text",
                        "text": meter_id,
                        "size": "xs",
                        "weight": "bold",
                        "align": "center",
                        "color": text_color,
                    }
                ],
            }
        )

    rows = [
        {"type": "box", "layout": "horizontal", "spacing": "xs", "contents": meter_boxes[:4]},
        {"type": "box", "layout": "horizontal", "spacing": "xs", "contents": meter_boxes[4:]},
    ]
    if confirmed_meter_count is not None:
        denominator = total_count or len(DEFAULT_METER_IDS)
        rows.insert(
            0,
            {
                "type": "text",
                "text": f"บันทึกแล้ว {confirmed_meter_count}/{denominator} เครื่อง",
                "size": "xs",
                "color": CARD_COLORS["neutral_gray"],
                "wrap": True,
            },
        )
    return {"type": "box", "layout": "vertical", "spacing": "xs", "contents": rows}


def _text_with_actions(
    text: str,
    action_items: Iterable[tuple[str, str, str]],
) -> TextMessage:
    return TextMessage(
        text=text,
        quick_reply=_quick_reply_from_actions(list(action_items)),
    )


def build_help_menu_message() -> TextMessage:
    return _text_with_actions(
        text="ต้องการดูวิธีใช้งานส่วนไหนครับ?",
        action_items=(
            (
                HELP_FLOW_TOPICS[topic]["label"],
                "postback",
                build_postback_data(action=POSTBACK_HELP_FLOW, topic=topic),
            )
            for topic in HELP_MENU_TOPICS
        ),
    )


def build_help_flow_response(topic: str | None):
    topic_key = (topic or "").strip()
    help_topic = HELP_FLOW_TOPICS.get(topic_key)
    if not help_topic:
        return build_help_menu_message()

    text_message = _text_with_actions(
        text=help_topic["text"],
        action_items=(
            ("Help", "postback", build_postback_data(action=POSTBACK_HELP)),
            (
                "คำสั่งพิมพ์เอง",
                "postback",
                build_postback_data(action=POSTBACK_HELP_FLOW, topic=HELP_TOPIC_TEXT_COMMANDS),
            ),
        ),
    )
    image_urls = _help_flow_image_urls(topic_key)
    if not image_urls:
        return text_message

    original_url, preview_url = image_urls
    return [
        ImageMessage(original_content_url=original_url, preview_image_url=preview_url),
        text_message,
    ]


def _help_flow_image_urls(topic: str) -> tuple[str, str] | None:
    original_url = _help_flow_image_url(topic, preview=False)
    preview_url = _help_flow_image_url(topic, preview=True)
    if original_url and preview_url:
        return original_url, preview_url
    return None


def _help_flow_image_url(topic: str, *, preview: bool) -> str:
    suffix = "_PREVIEW_URL" if preview else "_URL"
    base_env = "HELP_FLOW_IMAGE_PREVIEW_BASE_URL" if preview else "HELP_FLOW_IMAGE_BASE_URL"
    assets = HELP_FLOW_PREVIEW_IMAGE_ASSETS if preview else HELP_FLOW_IMAGE_ASSETS

    direct_url = os.getenv(f"HELP_FLOW_IMAGE_{topic.upper()}{suffix}", "").strip()
    if _is_https_url(direct_url):
        return direct_url

    base_url = os.getenv(base_env, "").strip().rstrip("/")
    asset = assets.get(topic)
    if asset and _is_https_url(base_url):
        return f"{base_url}/{asset}"
    return ""


def _is_https_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def build_start_collection_card(
    batch_id: str | None = None,
    week: str | None = None,
    expected_meter_count: int = 8,
    next_meter_id: str | None = "M1",
    confirmed_meter_count: int = 0,
) -> FlexMessage:
    context = week or batch_id or "รอบสัปดาห์นี้"
    contents = {
        "type": "bubble",
        "styles": {"footer": {"separator": True}},
        "hero": {
            "type": "box",
            "layout": "vertical",
            "backgroundColor": CARD_COLORS["primary"],
            "contents": [
                {
                    "type": "text",
                    "text": "เริ่มบันทึกมิเตอร์",
                    "weight": "bold",
                    "size": "xl",
                    "color": CARD_COLORS["white"],
                    "wrap": True,
                },
                {
                    "type": "text",
                    "text": f"{context} M1-M{expected_meter_count}",
                    "size": "sm",
                    "color": "#EAF7EA",
                    "wrap": True,
                },
            ],
            "spacing": "xs",
            "paddingAll": CARD_PADDING,
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                _status_badge(
                    f"{confirmed_meter_count}/{expected_meter_count} เครื่อง",
                    color=CARD_COLORS["dark_green"],
                    background_color=CARD_COLORS["light_green"],
                ),
                {
                    "type": "text",
                    "text": "ระบบจะพาไปทีละเครื่อง ถ่ายรูปให้เห็นหน้าจอมิเตอร์ชัดเจน แล้วตรวจค่า OCR ก่อนบันทึก",
                    "size": "sm",
                    "color": CARD_COLORS["text"],
                    "wrap": True,
                },
                _metric_row("เครื่องถัดไป", next_meter_id or "-", color=CARD_COLORS["dark_green"]),
            ],
            "paddingAll": CARD_PADDING,
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                _postback_button(
                    "เริ่มบันทึก",
                    POSTBACK_START_COLLECTION,
                    style="primary",
                    color=CARD_COLORS["primary"],
                ),
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "contents": [
                        _postback_button("ดูสถานะ", POSTBACK_SHOW_STATUS),
                        _postback_button("ยกเลิก", POSTBACK_CANCEL_COLLECTION),
                    ],
                },
            ],
            "paddingAll": CARD_PADDING,
        },
    }
    return FlexMessage(
        alt_text="เริ่มบันทึกค่ามิเตอร์",
        contents=FlexContainer.from_dict(contents),
    )


def build_meter_request_message(meter_id: str) -> FlexMessage:
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
    contents = {
        "type": "bubble",
        "styles": {"footer": {"separator": True}},
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": CARD_PADDING,
            "contents": [
                _section_title("รอรูปมิเตอร์"),
                {
                    "type": "text",
                    "text": f"ถ่ายรูป {meter_id}",
                    "size": "xl",
                    "weight": "bold",
                    "color": CARD_COLORS["text"],
                    "wrap": True,
                },
                {
                    "type": "text",
                    "text": "ให้เห็นตัวเลขบนหน้าจอชัดเจน หากต้องการเปลี่ยนเครื่องให้เลือก M1-M8 ด้านล่าง",
                    "size": "sm",
                    "color": CARD_COLORS["neutral_gray"],
                    "wrap": True,
                },
                _meter_grid(current_meter_id=meter_id),
            ],
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "paddingAll": CARD_PADDING,
            "contents": [
                _postback_button("ข้าม", POSTBACK_SKIP_METER, meter_id=meter_id),
                _postback_button("ดูสถานะ", POSTBACK_SHOW_STATUS),
                _postback_button("ยกเลิก", POSTBACK_CANCEL_COLLECTION),
            ],
        },
    }
    return FlexMessage(
        alt_text=f"ถ่ายรูปเครื่อง {meter_id}",
        contents=FlexContainer.from_dict(contents),
        quick_reply=action,
    )

def build_confirmation_card(
    meter_id: str,
    current_value: Decimal,
    prev_value: Decimal,
    produced: Decimal,
    amount: Decimal,
    confidence_level: str = "high",
    confidence_warnings: Sequence[str] | None = None,
) -> FlexMessage:
    body_contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                _section_title("ตรวจพบค่า"),
                _status_badge(
                    meter_id,
                    color=CARD_COLORS["white"],
                    background_color=CARD_COLORS["primary"],
                ),
            ],
        },
        {
            "type": "text",
            "text": f"{_format_number(current_value)} kWh",
            "size": "xxl",
            "weight": "bold",
            "color": CARD_COLORS["dark_green"],
            "wrap": True,
        },
        _metric_row("ครั้งก่อน", f"{_format_number(prev_value)} kWh"),
        _metric_row("ผลิตเพิ่ม", f"{_format_number(produced)} kWh", color=CARD_COLORS["primary"]),
        _metric_row("รายได้", f"{_format_number(amount)} บาท", color=CARD_COLORS["data_blue"]),
    ]
    if confidence_level != "high":
        body_contents.append(
            {
                "type": "box",
                "layout": "vertical",
                "cornerRadius": "8px",
                "backgroundColor": "#FFF8E1",
                "paddingAll": "10px",
                "contents": [
                    {
                        "type": "text",
                        "text": _confidence_text(confidence_level, confidence_warnings),
                        "wrap": True,
                        "color": CARD_COLORS["warning_text"],
                        "size": "sm",
                    }
                ],
            }
        )
    body_contents.append(
        {
            "type": "text",
            "text": "ตรวจเครื่องและค่าก่อนกดยืนยัน",
            "size": "xs",
            "color": CARD_COLORS["neutral_gray"],
            "wrap": True,
        }
    )

    contents = {
        "type": "bubble",
        "styles": {"footer": {"separator": True}},
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "contents": body_contents,
            "paddingAll": CARD_PADDING,
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "contents": [
                _postback_button(
                    "ยืนยัน",
                    POSTBACK_CONFIRM_READING,
                    meter_id=meter_id,
                    style="primary",
                    color=CARD_COLORS["primary"],
                ),
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "contents": [
                        _postback_button("แก้ไข", POSTBACK_EDIT_READING, meter_id=meter_id),
                        _postback_button("ถ่ายใหม่", POSTBACK_RETAKE_PHOTO, meter_id=meter_id),
                    ],
                },
                _postback_button("ยกเลิก", POSTBACK_CANCEL_COLLECTION, style="link"),
            ],
            "paddingAll": CARD_PADDING,
        },
    }
    return FlexMessage(
        alt_text=f"ยืนยันค่ามิเตอร์ {meter_id}",
        contents=FlexContainer.from_dict(contents),
    )


def build_ocr_review_message(
    meter_id: str,
    current_value: Decimal,
    warnings: Sequence[str],
) -> TextMessage:
    warning_text = "\n".join(f"- {item}" for item in warnings[:3])
    return _text_with_actions(
        text=(
            "ค่า OCR นี้เสี่ยงผิดพลาดครับ\n"
            f"{meter_id}: {current_value} kWh\n"
            f"{warning_text}\n"
            f"กรุณาพิมพ์ค่าเอง เช่น {meter_id} 12508 หรือถ่ายใหม่"
        ),
        action_items=(
            ("แก้เอง", "message", f"{meter_id} "),
            ("ถ่ายใหม่", "postback", build_postback_data(action=POSTBACK_RETAKE_PHOTO, meter_id=meter_id)),
            ("ยืนยันว่าใช่", "postback", build_postback_data(action=POSTBACK_FORCE_CONFIRM_READING, meter_id=meter_id)),
        ),
    )


def _confidence_text(level: str, warnings: Sequence[str] | None) -> str:
    if warnings:
        return f"ควรตรวจสอบ: {warnings[0]}"
    if level == "medium":
        return "ควรตรวจสอบค่า OCR ก่อนยืนยัน"
    return "ค่า OCR นี้มีความเสี่ยง ควรแก้เองหรือถ่ายใหม่"


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


def build_status_card(
    meter_id: str | None,
    pending: str,
    progress_text: str,
    *,
    batch_id: str | None = None,
    week: str | None = None,
    confirmed_count: int | None = None,
    total_count: int | None = None,
    missing_meter_ids: Sequence[str] | None = None,
    next_meter: str | None = None,
) -> FlexMessage:
    title_context = week or batch_id or "รอบปัจจุบัน"
    count_text = (
        f"{confirmed_count}/{total_count} เครื่อง"
        if confirmed_count is not None and total_count is not None
        else "ยังไม่มี progress"
    )
    body_contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                _section_title("สถานะรอบบันทึก", color=CARD_COLORS["data_blue"]),
                _status_badge(
                    count_text,
                    color=CARD_COLORS["dark_green"],
                    background_color=CARD_COLORS["light_green"],
                ),
            ],
        },
        {"type": "text", "text": title_context, "size": "sm", "color": CARD_COLORS["neutral_gray"], "wrap": True},
    ]
    if meter_id:
        body_contents.append(_metric_row("เครื่องปัจจุบัน", meter_id, color=CARD_COLORS["dark_green"]))
    if pending:
        body_contents.append(_metric_row("รอยืนยัน", pending, color=CARD_COLORS["warning_text"]))
    if next_meter:
        body_contents.append(_metric_row("ต่อไป", next_meter, color=CARD_COLORS["primary"]))
    if progress_text:
        body_contents.append(
            {
                "type": "text",
                "text": progress_text,
                "size": "xs",
                "color": CARD_COLORS["neutral_gray"],
                "wrap": True,
            }
        )
    if missing_meter_ids is not None:
        body_contents.append(
            _meter_grid(
                current_meter_id=next_meter or meter_id,
                missing_meter_ids=missing_meter_ids,
                confirmed_meter_count=confirmed_count,
                total_count=total_count,
            )
        )
    if not meter_id and not pending and not progress_text and missing_meter_ids is None:
        body_contents.append(
            {
                "type": "text",
                "text": "ยังไม่มีข้อมูลรอบนี้ครับ",
                "size": "sm",
                "color": CARD_COLORS["text"],
                "wrap": True,
            }
        )
    contents = {
        "type": "bubble",
        "styles": {"footer": {"separator": True}},
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": CARD_PADDING,
            "contents": body_contents,
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": CARD_PADDING,
            "contents": [
                _postback_button(
                    "บันทึกต่อ",
                    POSTBACK_SELECT_METER if next_meter else POSTBACK_START_COLLECTION,
                    meter_id=next_meter,
                    style="primary",
                    color=CARD_COLORS["primary"],
                ),
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "contents": [
                        _postback_button("รายงานล่าสุด", POSTBACK_LATEST_REPORT),
                        _postback_button("Help", POSTBACK_HELP),
                    ],
                },
            ],
        },
    }
    return FlexMessage(
        alt_text="สถานะรอบบันทึก",
        contents=FlexContainer.from_dict(contents),
    )

def build_history_menu_message() -> TextMessage:
    return _text_with_actions(
        text="ประวัติการบันทึกมิเตอร์\n\nเลือกรายการที่ต้องการดูครับ",
        action_items=(
            ("รอบปัจจุบัน", "postback", build_postback_data(action=POSTBACK_HISTORY_CURRENT)),
            ("สัปดาห์ก่อน", "postback", build_postback_data(action=POSTBACK_HISTORY_PREVIOUS)),
            ("เลือกรอบย้อนหลัง", "postback", build_postback_data(action=POSTBACK_HISTORY_SELECT_WEEK)),
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

def build_history_batch_list_message(summaries: Sequence) -> TextMessage:
    if not summaries:
        return build_history_empty_message("ยังไม่มีประวัติย้อนหลังใน 1 เดือนนี้ครับ")

    lines = ["ประวัติย้อนหลัง 1 เดือน", "", "เลือกรอบที่ต้องการดูครับ"]
    for summary in summaries:
        label = summary.week or summary.batch_id
        lines.append(f"{label}: {summary.confirmed_meter_count}/{summary.expected_meter_count} เครื่อง")

    items = [
        (
            summary.week or summary.batch_id,
            "postback",
            build_postback_data(action=POSTBACK_HISTORY_BATCH, batch_id=summary.batch_id),
        )
        for summary in summaries
    ]
    items.append(("กลับประวัติ", "postback", build_postback_data(action=POSTBACK_HISTORY)))
    return _text_with_actions(text="\n".join(lines), action_items=items)

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
            ("นำเข้ารายงานเก่า", "postback", build_postback_data(action=POSTBACK_SETTINGS_IMPORT_REPORT)),
        ),
    )

def build_report_import_prompt_message() -> TextMessage:
    return _text_with_actions(
        text=(
            "นำข้อมูลเข้าด้วยรายงานเก่า\n\n"
            "ส่งรูปรายงานเก่าเป็นรูปภาพได้เลยครับ "
            "ระบบจะอ่านตารางและให้ตรวจสอบก่อนบันทึก"
        ),
        action_items=(
            ("ยกเลิก", "postback", build_postback_data(action=POSTBACK_CANCEL_IMPORT_REPORT)),
            ("กลับตั้งค่า", "postback", build_postback_data(action=POSTBACK_SETTINGS)),
        ),
    )

def build_report_import_preview_message(pending) -> TextMessage:
    lines = [
        "ตรวจสอบรายงานก่อนนำเข้า",
        "",
        f"วันที่: {pending.date or '-'}",
        f"รอบ: {pending.week or '-'}",
        f"อ่านได้: {len(pending.rows)}/8 แถว",
        f"รวมผลิต: {_format_number(pending.total_produced_unit)} kWh",
        f"ยอดเงินรวม: {_format_number(pending.total_amount)} บาท",
    ]
    if pending.warnings:
        lines.extend(["", "คำเตือน:"])
        lines.extend(f"- {item}" for item in pending.warnings[:3])
    if pending.errors:
        lines.extend(["", "ข้อผิดพลาด:"])
        lines.extend(f"- {item}" for item in pending.errors[:3])

    actions: list[tuple[str, str, str]] = []
    if _can_confirm_report_import(pending):
        actions.append((
            "ยืนยันนำเข้า",
            "postback",
            build_postback_data(action=POSTBACK_CONFIRM_IMPORT_REPORT),
        ))
    actions.append(("ยกเลิก", "postback", build_postback_data(action=POSTBACK_CANCEL_IMPORT_REPORT)))
    actions.append(("กลับตั้งค่า", "postback", build_postback_data(action=POSTBACK_SETTINGS)))
    return _text_with_actions(text="\n".join(lines), action_items=actions)

def build_report_import_success_message(batch_id: str, week: str) -> TextMessage:
    return _text_with_actions(
        text=(
            "นำเข้ารายงานเก่าเรียบร้อยครับ\n\n"
            f"รอบ: {week}\n"
            "บันทึกครบ 8/8 เครื่อง และสร้างรูปรายงานแล้ว"
        ),
        action_items=(
            ("ดูประวัติ", "postback", build_postback_data(action=POSTBACK_HISTORY_BATCH, batch_id=batch_id)),
            (
                "ดูรายละเอียด",
                "postback",
                build_postback_data(action=POSTBACK_HISTORY_BATCH_DETAIL, batch_id=batch_id),
            ),
            ("รายงานล่าสุด", "postback", build_postback_data(action=POSTBACK_LATEST_REPORT, batch_id=batch_id)),
        ),
    )

def build_report_import_duplicate_message(batch_id: str, week: str) -> TextMessage:
    return _text_with_actions(
        text=(
            "รอบนี้มีข้อมูลอยู่แล้วครับ\n\n"
            f"รอบ: {week or batch_id}\n"
            "เวอร์ชันนี้ยังไม่รองรับการแทนที่หรือรวมข้อมูล"
        ),
        action_items=(
            ("ดูรายละเอียด", "postback", build_postback_data(action=POSTBACK_HISTORY_BATCH_DETAIL, batch_id=batch_id)),
            ("รายงานล่าสุด", "postback", build_postback_data(action=POSTBACK_LATEST_REPORT, batch_id=batch_id)),
            ("กลับตั้งค่า", "postback", build_postback_data(action=POSTBACK_SETTINGS)),
        ),
    )

def _can_confirm_report_import(pending) -> bool:
    return bool(
        pending.batch_id
        and pending.week
        and len(pending.rows) == 8
        and not pending.errors
        and not pending.duplicate
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
