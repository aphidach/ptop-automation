from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
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
    POSTBACK_SETTINGS_SYNC_SHEETS,
    POSTBACK_SETTINGS_VIEW,
    POSTBACK_SELECT_METER,
    POSTBACK_SKIP_METER,
    POSTBACK_SHOW_STATUS,
    POSTBACK_START_COLLECTION,
)
from app.report.generator import build_report_data

QUICK_TEXT_LIMIT = 20
LINE_QUICK_REPLY_ITEM_LIMIT = 13
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
LINE_CARD_START_COLLECTION_HERO_ASSET = "solar-meter-mascot-hero-v0.2.0.png"

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


def _postback_menu_row(
    label: str,
    action: str,
    *,
    description: str | None = None,
    **kwargs: str | int | bool | None,
) -> dict:
    text_contents = [
        {
            "type": "text",
            "text": label,
            "size": "sm",
            "weight": "bold",
            "color": CARD_COLORS["text"],
            "wrap": True,
        }
    ]
    if description:
        text_contents.append(
            {
                "type": "text",
                "text": description,
                "size": "xs",
                "color": CARD_COLORS["neutral_gray"],
                "wrap": True,
                "margin": "xs",
            }
        )

    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "alignItems": "center",
        "paddingAll": "10px",
        "cornerRadius": "8px",
        "borderWidth": "1px",
        "borderColor": "#E0E0E0",
        "action": {
            "type": "postback",
            "label": label[:QUICK_TEXT_LIMIT],
            "data": build_postback_data(action=action, **kwargs),
            "displayText": label,
        },
        "contents": [
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "none",
                "contents": text_contents,
                "flex": 1,
            },
            {
                "type": "text",
                "text": ">",
                "size": "md",
                "color": CARD_COLORS["data_blue"],
                "align": "end",
                "flex": 0,
            },
        ],
    }


def _settings_menu_row(
    icon: str,
    label: str,
    value: str,
    action: str,
    **kwargs: str | int | bool | None,
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
            "data": build_postback_data(action=action, **kwargs),
            "displayText": label,
        },
        "contents": [
            {
                "type": "text",
                "text": icon,
                "size": "sm",
                "weight": "bold",
                "color": CARD_COLORS["dark_green"],
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
                "size": "xs",
                "color": CARD_COLORS["text"],
                "align": "end",
                "wrap": True,
                "flex": 5,
            },
            {
                "type": "text",
                "text": ">",
                "size": "sm",
                "color": CARD_COLORS["neutral_gray"],
                "align": "end",
                "flex": 0,
            },
        ],
    }


def _settings_menu_list(rows: Sequence[dict]) -> dict:
    contents = []
    for index, row in enumerate(rows):
        if index:
            contents.append({"type": "separator", "color": "#E0E0E0"})
        contents.append(row)
    return {
        "type": "box",
        "layout": "vertical",
        "cornerRadius": "8px",
        "borderWidth": "1px",
        "borderColor": "#E0E0E0",
        "contents": contents,
    }


def _message_button(
    label: str,
    text: str,
    *,
    style: str = "secondary",
    height: str = "sm",
) -> dict:
    return {
        "type": "button",
        "style": style,
        "height": height,
        "action": {
            "type": "message",
            "label": label[:QUICK_TEXT_LIMIT],
            "text": text[:200],
        },
    }


def _section_title(text: str, *, color: str = CARD_COLORS["dark_green"]) -> dict:
    return {
        "type": "text",
        "text": text,
        "weight": "bold",
        "size": "sm",
        "color": color,
        "wrap": True,
    }


def _status_badge(
    label: str,
    *,
    tone: str = "success",
    color: str | None = None,
    background_color: str | None = None,
) -> dict:
    tone_styles = {
        "success": {
            "color": CARD_COLORS["dark_green"],
            "background_color": CARD_COLORS["light_green"],
        },
        "warning": {
            "color": CARD_COLORS["warning_text"],
            "background_color": "#FFF8E1",
        },
    }
    palette = tone_styles.get(tone, tone_styles["success"])

    return {
        "type": "box",
        "layout": "vertical",
        "cornerRadius": "12px",
        "paddingAll": "6px",
        "backgroundColor": background_color or palette["background_color"],
        "contents": [
            {
                "type": "text",
                "text": label,
                "size": "xs",
                "weight": "bold",
                "align": "center",
                "color": color or palette["color"],
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


def _has_display_value(value: str | None) -> bool:
    return value is not None and str(value).strip() not in {"", "-"}


def _optional_metric_rows(rows: Sequence[tuple[str, str | None, str | None]]) -> list[dict]:
    return [
        _metric_row(label, str(value), color=color or CARD_COLORS["text"])
        for label, value, color in rows
        if _has_display_value(value)
    ]


def _step_badge(label: str) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "width": "32px",
        "height": "32px",
        "cornerRadius": "16px",
        "backgroundColor": CARD_COLORS["primary"],
        "justifyContent": "center",
        "contents": [
            {
                "type": "text",
                "text": label,
                "size": "sm",
                "weight": "bold",
                "align": "center",
                "color": CARD_COLORS["white"],
            }
        ],
    }


def _body_text(text: str, *, color: str = CARD_COLORS["text"], size: str = "sm") -> dict:
    return {
        "type": "text",
        "text": text,
        "size": size,
        "color": color,
        "wrap": True,
    }


def _kwh_display_value(value: str) -> str:
    text = str(value).strip()
    if not _has_display_value(text):
        return "-"
    try:
        Decimal(text.replace(",", ""))
    except (InvalidOperation, ValueError):
        return text
    return f"{text} kWh"


def _card_header(
    *,
    title: str,
    subtitle: str | None = None,
    step_badge: str | None = None,
    hero_image_url: str | None = None,
) -> dict:
    title_contents = [
        {
            "type": "text",
            "text": title,
            "weight": "bold",
            "size": "xl",
            "color": CARD_COLORS["dark_green"],
            "wrap": True,
        }
    ]
    if subtitle:
        title_contents.append(
            {
                "type": "text",
                "text": subtitle,
                "size": "sm",
                "color": CARD_COLORS["neutral_gray"],
                "wrap": True,
                "margin": "xs",
            }
        )

    left_contents = []
    if step_badge:
        left_contents.append(_step_badge(step_badge))
    left_contents.append(
        {
            "type": "box",
            "layout": "vertical",
            "spacing": "none",
            "contents": title_contents,
            "flex": 1,
        }
    )

    row_contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "spacing": "md",
            "alignItems": "center",
            "contents": left_contents,
            "flex": 5 if hero_image_url else 1,
        }
    ]
    if hero_image_url:
        row_contents.append(
            {
                "type": "image",
                "url": hero_image_url,
                "size": "full",
                "aspectRatio": "1:1",
                "aspectMode": "fit",
                "flex": 2,
            }
        )

    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "md",
        "alignItems": "center",
        "contents": row_contents,
    }


def _card_shell(
    *,
    alt_text: str,
    title: str,
    subtitle: str | None = None,
    step_badge: str | None = None,
    status_badge: str | None = None,
    status_badge_tone: str = "success",
    hero_image_url: str | None = None,
    body_contents: Sequence[dict] = (),
    primary_action: dict | None = None,
    secondary_actions: Sequence[dict] = (),
    quick_actions: Sequence[tuple[str, str, str]] = (),
) -> FlexMessage:
    visible_secondary_actions = list(secondary_actions)[:2]
    contents = {
        "type": "bubble",
        "styles": {"footer": {"separator": True}},
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": CARD_PADDING,
            "contents": [
                _card_header(
                    title=title,
                    subtitle=subtitle,
                    step_badge=step_badge,
                    hero_image_url=hero_image_url,
                ),
            ],
        },
    }
    if status_badge:
        contents["body"]["contents"].append(
            _status_badge(
                status_badge,
                tone=status_badge_tone,
            )
        )
    contents["body"]["contents"].extend(body_contents)

    footer_contents = []
    if primary_action:
        footer_contents.append(primary_action)
    if len(visible_secondary_actions) == 1:
        footer_contents.append(visible_secondary_actions[0])
    elif visible_secondary_actions:
        footer_contents.append(
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": visible_secondary_actions,
            }
        )
    if footer_contents:
        contents["footer"] = {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": CARD_PADDING,
            "contents": footer_contents,
        }

    return FlexMessage(
        alt_text=alt_text,
        contents=FlexContainer.from_dict(contents),
        quick_reply=_quick_reply_from_actions(quick_actions) if quick_actions else None,
    )


def _meter_grid(
    *,
    current_meter_id: str | None = None,
    missing_meter_ids: Sequence[str] | None = None,
    confirmed_meter_count: int | None = None,
    total_count: int | None = None,
    meter_ids: Sequence[str] | None = None,
) -> dict:
    missing = set(missing_meter_ids or ())
    if meter_ids is not None:
        display_meter_ids = list(meter_ids)
    else:
        display_meter_ids = DEFAULT_METER_IDS[:total_count] if total_count else DEFAULT_METER_IDS
    meter_boxes = []
    for meter_id in display_meter_ids:
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
        {"type": "box", "layout": "horizontal", "spacing": "xs", "contents": meter_boxes[index:index + 4]}
        for index in range(0, len(meter_boxes), 4)
    ]
    if confirmed_meter_count is not None:
        denominator = (
            len(display_meter_ids)
            if total_count is None and meter_ids is not None
            else (total_count or len(DEFAULT_METER_IDS))
        )
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


def _meter_select_grid(meter_ids: Sequence[str]) -> dict:
    meter_boxes = [
        {
            "type": "box",
            "layout": "vertical",
            "height": "44px",
            "cornerRadius": "8px",
            "borderWidth": "1px",
            "borderColor": "#C8E6C9",
            "backgroundColor": CARD_COLORS["light_green"],
            "justifyContent": "center",
            "action": {
                "type": "postback",
                "label": meter_id[:QUICK_TEXT_LIMIT],
                "data": build_postback_data(action=POSTBACK_HISTORY_METER, meter_id=meter_id),
                "displayText": meter_id,
            },
            "contents": [
                {
                    "type": "text",
                    "text": meter_id,
                    "size": "sm",
                    "weight": "bold",
                    "align": "center",
                    "color": CARD_COLORS["dark_green"],
                }
            ],
            "flex": 1,
        }
        for meter_id in meter_ids
    ]
    rows = [
        {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "contents": meter_boxes[index:index + 4],
        }
        for index in range(0, len(meter_boxes), 4)
    ]
    return {"type": "box", "layout": "vertical", "spacing": "sm", "contents": rows}


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


def _line_card_asset_url(asset_name: str, direct_env: str | None = None) -> str | None:
    if direct_env:
        direct_url = os.getenv(direct_env, "").strip()
        if direct_url:
            return direct_url if _is_https_url(direct_url) else None

    base_url = os.getenv("LINE_CARD_IMAGE_BASE_URL", "").strip().rstrip("/")
    if _is_https_url(base_url):
        return f"{base_url}/{asset_name}"
    return None


def _start_collection_hero_url() -> str | None:
    return _line_card_asset_url(
        LINE_CARD_START_COLLECTION_HERO_ASSET,
        "LINE_CARD_START_COLLECTION_HERO_URL",
    )


def build_start_collection_card(
    batch_id: str | None = None,
    week: str | None = None,
    expected_meter_count: int = 8,
    next_meter_id: str | None = "M1",
    confirmed_meter_count: int = 0,
) -> FlexMessage:
    context = week or batch_id or "รอบสัปดาห์นี้"
    body_contents = [
        _body_text("เริ่มต้นบันทึกค่ามิเตอร์ เพื่อสร้างรายงานประจำสัปดาห์"),
        *_optional_metric_rows(
            (
                ("เครื่องถัดไป", next_meter_id, CARD_COLORS["dark_green"]),
            )
        ),
    ]
    return _card_shell(
        alt_text="เริ่มบันทึกค่ามิเตอร์",
        title="เริ่มบันทึกมิเตอร์",
        subtitle=f"{context} M1-M{expected_meter_count}",
        step_badge="1",
        status_badge=f"{confirmed_meter_count}/{expected_meter_count} เครื่อง",
        hero_image_url=_start_collection_hero_url(),
        body_contents=body_contents,
        primary_action=_postback_button(
            "เริ่มบันทึก",
            POSTBACK_START_COLLECTION,
            style="primary",
            color=CARD_COLORS["primary"],
        ),
        secondary_actions=(
            _postback_button("ดูสถานะ", POSTBACK_SHOW_STATUS),
        ),
        quick_actions=(
            ("ยกเลิก", "postback", build_postback_data(action=POSTBACK_CANCEL_COLLECTION)),
        ),
    )


def build_meter_request_message(
    meter_id: str,
    meter_ids: Sequence[str] | None = None,
) -> FlexMessage:
    meter_id_list = list(meter_ids or DEFAULT_METER_IDS)
    visible_meter_ids = meter_id_list[: LINE_QUICK_REPLY_ITEM_LIMIT - 3]
    if meter_id in meter_id_list and meter_id not in visible_meter_ids:
        visible_meter_ids = [*visible_meter_ids[:-1], meter_id]
    meter_actions = [
        (target, "postback", build_postback_data(action=POSTBACK_SELECT_METER, meter_id=target))
        for target in visible_meter_ids
    ]
    return _card_shell(
        alt_text=f"ถ่ายรูปเครื่อง {meter_id}",
        title="รอรูปมิเตอร์",
        subtitle=f"ถ่ายรูป {meter_id}",
        body_contents=[
            _body_text("ให้เห็นตัวเลขบนหน้าจอชัดเจน หากต้องการเปลี่ยนเครื่องให้เลือกด้านล่าง"),
            _meter_grid(current_meter_id=meter_id, meter_ids=meter_id_list),
        ],
        quick_actions=(
            ("ข้าม", "postback", build_postback_data(action=POSTBACK_SKIP_METER, meter_id=meter_id)),
            *meter_actions,
            ("ดูสถานะ", "postback", build_postback_data(action=POSTBACK_SHOW_STATUS)),
            ("ยกเลิก", "postback", build_postback_data(action=POSTBACK_CANCEL_COLLECTION)),
        ),
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

    return _card_shell(
        alt_text=f"ยืนยันค่ามิเตอร์ {meter_id}",
        title="ยืนยันค่ามิเตอร์",
        subtitle=f"มิเตอร์ {meter_id}",
        body_contents=body_contents,
        primary_action=_postback_button(
            "ยืนยัน",
            POSTBACK_CONFIRM_READING,
            meter_id=meter_id,
            style="primary",
            color=CARD_COLORS["primary"],
        ),
        secondary_actions=(
            _postback_button("แก้ไข", POSTBACK_EDIT_READING, meter_id=meter_id),
            _postback_button("ถ่ายใหม่", POSTBACK_RETAKE_PHOTO, meter_id=meter_id),
        ),
        quick_actions=(
            ("ยกเลิก", "postback", build_postback_data(action=POSTBACK_CANCEL_COLLECTION)),
        ),
    )


def build_ocr_review_message(
    meter_id: str,
    current_value: Decimal,
    warnings: Sequence[str],
) -> FlexMessage:
    warning_text = "\n".join(warnings[:3]) if warnings else "ควรตรวจสอบค่า OCR ก่อนบันทึก"
    return _warning_recovery_card(
        meter_id=meter_id,
        reason="ค่า OCR นี้เสี่ยงผิดพลาด",
        guidance=f"พิมพ์ค่าเอง เช่น {meter_id} 12508 หรือถ่ายใหม่",
        rows=(
            ("ค่าที่อ่านได้", f"{_format_number(current_value)} kWh"),
            ("เหตุผล", warning_text),
        ),
        footer_buttons=(
            _postback_button(
                "ยืนยันว่าใช่",
                POSTBACK_FORCE_CONFIRM_READING,
                meter_id=meter_id,
                style="primary",
                color=CARD_COLORS["energy_yellow"],
            ),
            _postback_button("แก้ไข", POSTBACK_EDIT_READING, meter_id=meter_id),
            _postback_button("ถ่ายใหม่", POSTBACK_RETAKE_PHOTO, meter_id=meter_id),
        ),
        quick_actions=(
            ("แก้เอง", "message", f"{meter_id} "),
            ("ดูสถานะ", "postback", build_postback_data(action=POSTBACK_SHOW_STATUS)),
            ("ยกเลิก", "postback", build_postback_data(action=POSTBACK_CANCEL_COLLECTION)),
        ),
    )


def _confidence_text(level: str, warnings: Sequence[str] | None) -> str:
    if warnings:
        return f"ควรตรวจสอบ: {warnings[0]}"
    if level == "medium":
        return "ควรตรวจสอบค่า OCR ก่อนยืนยัน"
    return "ค่า OCR นี้มีความเสี่ยง ควรแก้เองหรือถ่ายใหม่"


def _warning_recovery_card(
    *,
    meter_id: str,
    reason: str,
    guidance: str,
    rows: Sequence[tuple[str, str]] = (),
    footer_buttons: Sequence[dict] = (),
    quick_actions: Sequence[tuple[str, str, str]] = (),
) -> FlexMessage:
    body_contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "spacing": "md",
            "contents": [
                _section_title("ตรวจสอบก่อนบันทึก", color=CARD_COLORS["warning_text"]),
                _status_badge(meter_id, tone="warning"),
            ],
        },
        {
            "type": "box",
            "layout": "vertical",
            "cornerRadius": "8px",
            "backgroundColor": "#FFF8E1",
            "paddingAll": "10px",
            "contents": [
                {
                    "type": "text",
                    "text": reason,
                    "size": "sm",
                    "weight": "bold",
                    "color": CARD_COLORS["warning_text"],
                    "wrap": True,
                },
                {
                    "type": "text",
                    "text": guidance,
                    "size": "xs",
                    "color": CARD_COLORS["text"],
                    "wrap": True,
                    "margin": "xs",
                },
            ],
        },
    ]
    body_contents.extend(_metric_row(label, value) for label, value in rows)

    primary_action = None
    secondary_actions: list[dict] = []
    for button in footer_buttons:
        if button.get("style") == "primary" and primary_action is None:
            primary_action = button
            continue
        secondary_actions.append(button)
    if not secondary_actions and primary_action is None:
        secondary_actions.append(_postback_button("ดูสถานะ", POSTBACK_SHOW_STATUS))

    return _card_shell(
        alt_text=f"ตรวจสอบค่ามิเตอร์ {meter_id}",
        title="ตรวจสอบก่อนบันทึก",
        subtitle=f"มิเตอร์ {meter_id}",
        status_badge="คำเตือน",
        status_badge_tone="warning",
        body_contents=body_contents,
        primary_action=primary_action,
        secondary_actions=secondary_actions,
        quick_actions=quick_actions,
    )


def build_duplicate_warning_card(
    meter_id: str,
    old_value: str,
    new_value: str,
) -> FlexMessage:
    return _warning_recovery_card(
        meter_id=meter_id,
        reason=f"รอบนี้มีค่า {meter_id} แล้ว",
        guidance="เวอร์ชันนี้ยังไม่รองรับการแทนที่ข้อมูล ให้ตรวจสถานะหรือถ่ายใหม่",
        rows=(
            ("ค่าเดิม", _kwh_display_value(old_value)),
            ("ค่าใหม่", _kwh_display_value(new_value)),
        ),
        footer_buttons=(
            _postback_button("ถ่ายใหม่", POSTBACK_RETAKE_PHOTO, meter_id=meter_id),
            _postback_button("ดูสถานะ", POSTBACK_SHOW_STATUS),
        ),
        quick_actions=(
            ("ยกเลิก", "postback", build_postback_data(action=POSTBACK_CANCEL_COLLECTION)),
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


def build_unreadable_prompt(meter_id: str) -> FlexMessage:
    return _warning_recovery_card(
        meter_id=meter_id,
        reason="อ่านตัวเลขจากรูปนี้ไม่ชัด",
        guidance=f"พิมพ์ค่าเอง เช่น {meter_id} 12508 หรือถ่ายใหม่",
        footer_buttons=(
            _postback_button("ถ่ายใหม่", POSTBACK_RETAKE_PHOTO, meter_id=meter_id),
            _postback_button("ดูสถานะ", POSTBACK_SHOW_STATUS),
        ),
        quick_actions=(
            ("แก้เอง", "message", f"{meter_id} "),
            ("ยกเลิก", "postback", build_postback_data(action=POSTBACK_CANCEL_COLLECTION)),
        ),
    )


def build_lower_value_warning(meter_id: str, prev_value: Decimal, cur_value: Decimal) -> FlexMessage:
    return _warning_recovery_card(
        meter_id=meter_id,
        reason="ค่าที่อ่านได้ต่ำกว่าครั้งก่อน",
        guidance="ตรวจเลขบนมิเตอร์ก่อนยืนยัน ถ้า OCR ผิดให้แก้ไขหรือถ่ายใหม่",
        rows=(
            ("ครั้งก่อน", f"{_format_number(prev_value)} kWh"),
            ("ครั้งนี้", f"{_format_number(cur_value)} kWh"),
        ),
        footer_buttons=(
            _postback_button(
                "ยืนยันว่าใช่",
                POSTBACK_FORCE_CONFIRM_READING,
                meter_id=meter_id,
                style="primary",
                color=CARD_COLORS["energy_yellow"],
            ),
            _postback_button("แก้ไข", POSTBACK_EDIT_READING, meter_id=meter_id),
            _postback_button("ถ่ายใหม่", POSTBACK_RETAKE_PHOTO, meter_id=meter_id),
        ),
        quick_actions=(
            ("แก้เอง", "message", f"{meter_id} "),
            ("ดูสถานะ", "postback", build_postback_data(action=POSTBACK_SHOW_STATUS)),
            ("ยกเลิก", "postback", build_postback_data(action=POSTBACK_CANCEL_COLLECTION)),
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
        *_optional_metric_rows(
            (
                ("เครื่องปัจจุบัน", meter_id, CARD_COLORS["dark_green"]),
                ("รอยืนยัน", pending, CARD_COLORS["warning_text"]),
                ("ต่อไป", next_meter, CARD_COLORS["primary"]),
            )
        ),
    ]
    if progress_text:
        body_contents.append(_body_text(progress_text, color=CARD_COLORS["neutral_gray"], size="xs"))
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
        body_contents.append(_body_text("ยังไม่มีข้อมูลรอบนี้ครับ"))

    primary_action = None
    if next_meter:
        primary_action = _postback_button(
            "บันทึกต่อ",
            POSTBACK_SELECT_METER,
            meter_id=next_meter,
            style="primary",
            color=CARD_COLORS["primary"],
        )

    return _card_shell(
        alt_text="สถานะรอบบันทึก",
        title="สถานะรอบบันทึก",
        subtitle=title_context,
        status_badge=count_text,
        body_contents=body_contents,
        primary_action=primary_action,
        secondary_actions=(
            _postback_button("รายงานล่าสุด", POSTBACK_LATEST_REPORT),
            _postback_button("Help", POSTBACK_HELP),
        ),
    )


def build_batch_complete_card(
    *,
    batch_id: str,
    week: str | None = None,
    expected_meter_count: int = 8,
    report_status: str = "กำลังสร้างรายงาน",
) -> FlexMessage:
    title_context = week or batch_id
    body_contents = [
        _status_badge(
            "บันทึกครบแล้ว",
            color=CARD_COLORS["white"],
            background_color=CARD_COLORS["primary"],
        ),
        {
            "type": "text",
            "text": "บันทึกครบแล้ว",
            "size": "xl",
            "weight": "bold",
            "color": CARD_COLORS["dark_green"],
            "wrap": True,
        },
        _metric_row("รอบ", title_context, color=CARD_COLORS["dark_green"]),
        _metric_row(
            "สถานะ",
            f"ครบ {expected_meter_count}/{expected_meter_count} เครื่อง",
            color=CARD_COLORS["primary"],
        ),
        {
            "type": "box",
            "layout": "vertical",
            "cornerRadius": "8px",
            "backgroundColor": CARD_COLORS["light_green"],
            "paddingAll": "10px",
            "contents": [
                {
                    "type": "text",
                    "text": report_status,
                    "size": "sm",
                    "color": CARD_COLORS["dark_green"],
                    "weight": "bold",
                    "wrap": True,
                }
            ],
        },
    ]

    return _card_shell(
        alt_text="บันทึกครบแล้ว กำลังสร้างรายงาน",
        title="บันทึกครบแล้ว",
        status_badge="เสร็จสิ้น",
        status_badge_tone="success",
        body_contents=body_contents,
        secondary_actions=(
            _postback_button("ประวัติ", POSTBACK_HISTORY_BATCH, batch_id=batch_id),
            _postback_button("ดูสถานะ", POSTBACK_SHOW_STATUS),
        ),
    )


def build_history_menu_message() -> FlexMessage:
    return _card_shell(
        alt_text="ประวัติการบันทึก",
        title="ประวัติ",
        subtitle="เลือกข้อมูลที่ต้องการดู",
        body_contents=(
            _body_text(
                "เลือกเส้นทางด้านล่างเพื่อดูข้อมูลย้อนหลัง",
                size="sm",
                color=CARD_COLORS["text"],
            ),
            _postback_menu_row(
                "รอบปัจจุบัน",
                POSTBACK_HISTORY_CURRENT,
                description="ดูข้อมูลรอบที่กำลังบันทึก",
            ),
            _postback_menu_row(
                "สัปดาห์ก่อน",
                POSTBACK_HISTORY_PREVIOUS,
                description="ดูรอบก่อนหน้าล่าสุด",
            ),
            _postback_menu_row(
                "เลือกรอบย้อนหลัง",
                POSTBACK_HISTORY_SELECT_WEEK,
                description="เลือกรายการย้อนหลัง 1 เดือน",
            ),
            _postback_menu_row(
                "ดูตามมิเตอร์",
                POSTBACK_HISTORY_METER,
                description="ดูประวัติรายเครื่อง",
            ),
        ),
        secondary_actions=(
            _postback_button("รายงานล่าสุด", POSTBACK_LATEST_REPORT),
            _postback_button("Help", POSTBACK_HELP),
        ),
        quick_actions=(
            ("รอบปัจจุบัน", "postback", build_postback_data(action=POSTBACK_HISTORY_CURRENT)),
            ("สัปดาห์ก่อน", "postback", build_postback_data(action=POSTBACK_HISTORY_PREVIOUS)),
            ("เลือกรอบย้อนหลัง", "postback", build_postback_data(action=POSTBACK_HISTORY_SELECT_WEEK)),
            ("ดูตามมิเตอร์", "postback", build_postback_data(action=POSTBACK_HISTORY_METER)),
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

def build_history_summary_message(title: str, summary) -> FlexMessage:
    week = summary.week or summary.batch_id
    progress = f"{summary.confirmed_meter_count}/{summary.expected_meter_count} เครื่อง"
    body_contents = [
        _metric_row("รอบ", week, color=CARD_COLORS["text"]),
        _metric_row("สถานะ", str(summary.status), color=CARD_COLORS["data_blue"]),
        _metric_row("บันทึกแล้ว", progress, color=CARD_COLORS["dark_green"]),
    ]
    if summary.missing_meter_ids:
        body_contents.append(
            _body_text(
                f"ยังขาด: {', '.join(summary.missing_meter_ids)}",
                color=CARD_COLORS["warning_text"],
                size="xs",
            )
        )
    body_contents.extend(
        (
            _metric_row("รวมผลิต", f"{_format_number(summary.produced_unit)} kWh", color=CARD_COLORS["dark_green"]),
            _metric_row("ยอดเงินรวม", f"{_format_number(summary.amount)} บาท", color=CARD_COLORS["primary"]),
        )
    )
    return _card_shell(
        alt_text=title,
        title=title,
        subtitle=week,
        status_badge=progress,
        body_contents=body_contents,
        primary_action=_postback_button(
            "ดูรายละเอียด",
            POSTBACK_HISTORY_BATCH_DETAIL,
            batch_id=summary.batch_id,
            style="primary",
            color=CARD_COLORS["primary"],
        ),
        secondary_actions=(
            _postback_button("บันทึกต่อ", POSTBACK_START_COLLECTION),
            _postback_button("ประวัติ", POSTBACK_HISTORY),
        ),
        quick_actions=(
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

def build_history_detail_message(summary) -> FlexMessage:
    week = summary.week or summary.batch_id
    by_meter = {str(row.get("meter_id", "")): row for row in summary.readings}
    detail_rows = []
    for meter_id in DEFAULT_METER_IDS:
        row = by_meter.get(meter_id)
        if not row:
            detail_rows.append(_metric_row(meter_id, "ยังไม่มีข้อมูล", color=CARD_COLORS["neutral_gray"]))
            continue
        current = _format_number(row.get("current_value", "0"))
        produced = _format_number(row.get("produced_unit", "0"))
        detail_rows.append(_metric_row(meter_id, f"{current} kWh (+{produced})", color=CARD_COLORS["dark_green"]))
    return _card_shell(
        alt_text=f"รายละเอียดรอบ {week}",
        title="รายละเอียดรอบ",
        subtitle=week,
        status_badge=f"{summary.confirmed_meter_count}/{summary.expected_meter_count} เครื่อง",
        body_contents=detail_rows,
        primary_action=_postback_button(
            "ส่งรูปรายงาน",
            POSTBACK_LATEST_REPORT,
            batch_id=summary.batch_id,
            style="primary",
            color=CARD_COLORS["primary"],
        ),
        secondary_actions=(
            _postback_button("ดูตามมิเตอร์", POSTBACK_HISTORY_METER),
            _postback_button("ประวัติ", POSTBACK_HISTORY),
        ),
        quick_actions=(
            ("ส่งรูปรายงาน", "postback", build_postback_data(action=POSTBACK_LATEST_REPORT, batch_id=summary.batch_id)),
            ("ดูตามมิเตอร์", "postback", build_postback_data(action=POSTBACK_HISTORY_METER)),
            ("บันทึกต่อ", "postback", build_postback_data(action=POSTBACK_START_COLLECTION)),
            ("กลับประวัติ", "postback", build_postback_data(action=POSTBACK_HISTORY)),
        ),
    )

def build_history_meter_select_message(meter_ids: Sequence[str] | None = None) -> FlexMessage:
    display_meter_ids = tuple(meter_ids or DEFAULT_METER_IDS)
    items = [
        (meter_id, "postback", build_postback_data(action=POSTBACK_HISTORY_METER, meter_id=meter_id))
        for meter_id in display_meter_ids
    ]
    items.append(("กลับประวัติ", "postback", build_postback_data(action=POSTBACK_HISTORY)))

    return _card_shell(
        alt_text="ดูตามมิเตอร์",
        title="ดูตามมิเตอร์",
        subtitle="เลือกมิเตอร์ที่ต้องการดู",
        body_contents=(
            _body_text(
                "แตะเครื่องด้านล่างเพื่อดูประวัติรายเครื่อง",
                size="sm",
                color=CARD_COLORS["text"],
            ),
            _meter_select_grid(display_meter_ids),
        ),
        secondary_actions=(
            _postback_button("กลับประวัติ", POSTBACK_HISTORY),
            _postback_button("รายงานล่าสุด", POSTBACK_LATEST_REPORT),
        ),
        quick_actions=items,
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
    expected_meter_count = settings_values.get("expected_meter_count", "8")
    default_rate = settings_values.get("default_rate", "4.2")
    report_title = settings_values.get("report_title", "Solar Weekly Report")

    quick_actions = (
        ("ดูค่าปัจจุบัน", "postback", build_postback_data(action=POSTBACK_SETTINGS_VIEW)),
        ("ดูรายชื่อมิเตอร์", "postback", build_postback_data(action=POSTBACK_SETTINGS_METERS)),
        ("ติดต่อผู้ดูแล", "postback", build_postback_data(action=POSTBACK_SETTINGS_CONTACT_ADMIN)),
        ("Help", "postback", build_postback_data(action=POSTBACK_HELP)),
    )
    if is_admin:
        quick_actions = (
            ("ดูรายชื่อมิเตอร์", "postback", build_postback_data(action=POSTBACK_SETTINGS_METERS)),
            ("อัตราค่าไฟ", "postback", build_postback_data(action=POSTBACK_SETTINGS_EDIT_RATE)),
            ("จำนวนเครื่อง", "postback", build_postback_data(action=POSTBACK_SETTINGS_EDIT_EXPECTED_COUNT)),
            ("ชื่อรายงาน", "postback", build_postback_data(action=POSTBACK_SETTINGS_EDIT_REPORT_TITLE)),
            ("ผู้รับรายงาน", "postback", build_postback_data(action=POSTBACK_SETTINGS_RECIPIENTS)),
            ("สิทธิ์ผู้ใช้งาน", "postback", build_postback_data(action=POSTBACK_SETTINGS_PERMISSIONS)),
            ("Sync Google Sheet", "postback", build_postback_data(action=POSTBACK_SETTINGS_SYNC_SHEETS)),
            ("นำเข้ารายงานเก่า", "postback", build_postback_data(action=POSTBACK_SETTINGS_IMPORT_REPORT)),
        )

    rate_action = POSTBACK_SETTINGS_EDIT_RATE if is_admin else POSTBACK_SETTINGS_VIEW
    count_action = POSTBACK_SETTINGS_EDIT_EXPECTED_COUNT if is_admin else POSTBACK_SETTINGS_VIEW
    title_action = POSTBACK_SETTINGS_EDIT_REPORT_TITLE if is_admin else POSTBACK_SETTINGS_VIEW
    role_badge = _status_badge(
        "Admin" if is_admin else "Operator",
        color=CARD_COLORS["white"] if is_admin else CARD_COLORS["text"],
        background_color=CARD_COLORS["neutral_gray"] if is_admin else CARD_COLORS["page_background"],
    )
    role_badge["flex"] = 0
    menu_rows = [
        _settings_menu_row(
            "kW",
            "อัตราค่าไฟ",
            _settings_rate_display(default_rate),
            rate_action,
        ),
        _settings_menu_row(
            "#",
            "จำนวนเครื่อง",
            f"{expected_meter_count} เครื่อง",
            count_action,
        ),
        _settings_menu_row(
            "R",
            "ชื่อรายงาน",
            report_title,
            title_action,
        ),
        _settings_menu_row(
            "M",
            f"มิเตอร์ M1-M{expected_meter_count}",
            "จัดการข้อมูลมิเตอร์" if is_admin else "ดูรายชื่อมิเตอร์",
            POSTBACK_SETTINGS_METERS,
        ),
    ]
    if is_admin:
        menu_rows.append(
            _settings_menu_row(
                "G",
                "Sync Google Sheet",
                "แทนที่ SQLite",
                POSTBACK_SETTINGS_SYNC_SHEETS,
            )
        )

    contents = {
        "type": "bubble",
        "styles": {"footer": {"separator": False}},
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": CARD_PADDING,
            "contents": [
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
                                    "text": "ตั้งค่าระบบ",
                                    "weight": "bold",
                                    "size": "xl",
                                    "color": CARD_COLORS["dark_green"],
                                    "wrap": True,
                                },
                                {
                                    "type": "text",
                                    "text": "เลือกเมนูที่ต้องการ",
                                    "size": "sm",
                                    "color": CARD_COLORS["neutral_gray"],
                                    "wrap": True,
                                    "margin": "xs",
                                },
                            ],
                            "flex": 1,
                        },
                        role_badge,
                    ],
                },
                _settings_menu_list(menu_rows),
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": CARD_PADDING,
            "contents": [
                _postback_button(
                    "ดูค่าปัจจุบัน",
                    POSTBACK_SETTINGS_VIEW,
                    style="primary",
                    color=CARD_COLORS["primary"],
                )
            ],
        },
    }

    return FlexMessage(
        alt_text="ตั้งค่าระบบ",
        contents=FlexContainer.from_dict(contents),
        quick_reply=_quick_reply_from_actions(quick_actions),
    )


def build_report_summary_message(
    batch_id: str,
    *,
    report_status: str = "พร้อมส่งรายงาน",
) -> FlexMessage | TextMessage:
    report = build_report_data(batch_id)
    if not report:
        return _text_with_actions(
            text=f"ยังไม่มีข้อมูลรายงานของ {batch_id} ครับ",
            action_items=(
                ("รายงานล่าสุด", "postback", build_postback_data(action=POSTBACK_LATEST_REPORT)),
            ),
        )

    week = report.week or batch_id
    reading_count = len(report.readings)
    body_contents = [
        _metric_row("สัปดาห์", week, color=CARD_COLORS["text"]),
        _metric_row("จำนวนเครื่อง", str(reading_count), color=CARD_COLORS["text"]),
        _metric_row("ผลผลิตรวม", f"{_format_number(report.total_produced_unit)} kWh", color=CARD_COLORS["dark_green"]),
        _metric_row("ยอดเงินรวม", f"{_format_number(report.total_amount)} บาท", color=CARD_COLORS["primary"]),
    ]

    return _card_shell(
        alt_text=f"รายงานสัปดาห์ {week}",
        title="สรุปรายงานสัปดาห์",
        subtitle=week,
        status_badge=report_status,
        body_contents=body_contents,
        primary_action=_postback_button(
            "ดูรายงานล่าสุด",
            POSTBACK_LATEST_REPORT,
            batch_id=batch_id,
            style="primary",
            color=CARD_COLORS["primary"],
        ),
        secondary_actions=(
            _postback_button("ดูรายละเอียด", POSTBACK_HISTORY_BATCH_DETAIL, batch_id=batch_id),
            _postback_button("ประวัติ", POSTBACK_HISTORY),
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
