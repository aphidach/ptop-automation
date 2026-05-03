from __future__ import annotations

import os

from linebot.v3.messaging import FlexContainer, FlexMessage, ImageMessage

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

from app.line.message_builders.assets import _is_https_url, _start_collection_hero_url
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


def _help_postback_data(topic: str) -> str:
    return build_postback_data(action=POSTBACK_HELP_FLOW, topic=topic)


def _help_section_header(title: str, action_label: str | None = None) -> dict:
    contents = [
        {
            "type": "text",
            "text": title,
            "size": "md",
            "weight": "bold",
            "color": CARD_COLORS["text"],
            "wrap": True,
            "flex": 1,
        }
    ]
    if action_label:
        contents.append(
            {
                "type": "text",
                "text": action_label,
                "size": "xs",
                "color": CARD_COLORS["data_blue"],
                "align": "end",
                "action": {
                    "type": "postback",
                    "label": action_label[:QUICK_TEXT_LIMIT],
                    "data": _help_postback_data(HELP_TOPIC_TEXT_COMMANDS),
                    "displayText": action_label,
                },
                "flex": 0,
            }
        )
    return {
        "type": "box",
        "layout": "horizontal",
        "alignItems": "center",
        "contents": contents,
    }


def _help_icon_box(
    icon: str,
    *,
    background_color: str = CARD_COLORS["light_green"],
    color: str = CARD_COLORS["dark_green"],
    size: str = "xl",
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
                "size": size,
                "weight": "bold",
                "color": color,
                "align": "center",
            }
        ],
    }


def _help_hero() -> dict:
    hero_image_url = _start_collection_hero_url()
    contents = [
        {
            "type": "box",
            "layout": "vertical",
            "spacing": "xs",
            "contents": [
                {
                    "type": "text",
                    "text": "ช่วยเหลือ",
                    "size": "xxl",
                    "weight": "bold",
                    "color": CARD_COLORS["dark_green"],
                    "wrap": True,
                },
                {
                    "type": "text",
                    "text": "ต้องการดูวิธีใช้งานส่วนไหนครับ?",
                    "size": "sm",
                    "color": CARD_COLORS["text"],
                    "wrap": True,
                },
            ],
            "flex": 3,
        }
    ]
    if hero_image_url:
        contents.append(
            {
                "type": "image",
                "url": hero_image_url,
                "size": "full",
                "aspectRatio": "1:1",
                "aspectMode": "fit",
                "flex": 2,
            }
        )
    else:
        contents.insert(
            0,
            _help_icon_box(
                "?",
                background_color="#DFF5E4",
                color=CARD_COLORS["dark_green"],
                size="xxl",
            ),
        )
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "md",
        "alignItems": "center",
        "paddingAll": "14px",
        "cornerRadius": "8px",
        "backgroundColor": "#F1F8F3",
        "contents": contents,
    }


def _help_action_tile(
    icon: str,
    label: str,
    description: str,
    action: str,
    **kwargs: str | int | bool | None,
) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "alignItems": "center",
        "paddingAll": "10px",
        "cornerRadius": "8px",
        "borderWidth": "1px",
        "borderColor": "#DDE3EA",
        "backgroundColor": CARD_COLORS["white"],
        "action": {
            "type": "postback",
            "label": label[:QUICK_TEXT_LIMIT],
            "data": build_postback_data(action=action, **kwargs),
            "displayText": label,
        },
        "contents": [
            _help_icon_box(icon, background_color=CARD_COLORS["white"]),
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "contents": [
                    {
                        "type": "text",
                        "text": label,
                        "size": "sm",
                        "weight": "bold",
                        "color": CARD_COLORS["text"],
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": description,
                        "size": "xs",
                        "color": CARD_COLORS["neutral_gray"],
                        "wrap": True,
                        "maxLines": 2,
                    },
                ],
                "flex": 1,
            },
        ],
    }


def _help_quick_grid() -> dict:
    tiles = [
        _help_action_tile(
            "▣",
            "บันทึกมิเตอร์",
            "วิธีถ่ายรูปและบันทึกค่า",
            POSTBACK_HELP_FLOW,
            topic=HELP_TOPIC_START_COLLECTION,
        ),
        _help_action_tile(
            "○",
            "ยืนยัน/แก้ OCR",
            "ตรวจสอบและแก้ไขตัวเลข",
            POSTBACK_HELP_FLOW,
            topic=HELP_TOPIC_CONFIRM_READING,
        ),
        _help_action_tile(
            "▥",
            "ดูสถานะ",
            "ดูความคืบหน้าและสถานะ",
            POSTBACK_SHOW_STATUS,
        ),
        _help_action_tile(
            "□",
            "รายงาน",
            "ดูรายงานและสรุปผล",
            POSTBACK_LATEST_REPORT,
        ),
    ]
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "contents": [
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": tiles[:2],
            },
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": tiles[2:],
            },
        ],
    }


def _help_menu_row(
    icon: str,
    label: str,
    description: str,
    topic: str,
    *,
    icon_background: str = CARD_COLORS["light_green"],
    icon_color: str = CARD_COLORS["dark_green"],
) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "alignItems": "center",
        "paddingAll": "10px",
        "cornerRadius": "8px",
        "borderWidth": "1px",
        "borderColor": "#E0E0E0",
        "backgroundColor": CARD_COLORS["white"],
        "action": {
            "type": "postback",
            "label": label[:QUICK_TEXT_LIMIT],
            "data": _help_postback_data(topic),
            "displayText": label,
        },
        "contents": [
            _help_icon_box(
                icon,
                background_color=icon_background,
                color=icon_color,
            ),
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "contents": [
                    {
                        "type": "text",
                        "text": label,
                        "size": "sm",
                        "weight": "bold",
                        "color": CARD_COLORS["text"],
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": description,
                        "size": "xs",
                        "color": CARD_COLORS["neutral_gray"],
                        "wrap": True,
                        "maxLines": 2,
                    },
                ],
                "flex": 1,
            },
            {
                "type": "text",
                "text": ">",
                "size": "lg",
                "color": CARD_COLORS["neutral_gray"],
                "align": "end",
                "flex": 0,
            },
        ],
    }


def _help_category_list() -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "contents": [
            _help_menu_row(
                "▤",
                "วิธีใช้งานพื้นฐาน",
                "เรียนรู้การใช้งานระบบตั้งแต่เริ่มต้น",
                HELP_TOPIC_START_COLLECTION,
                icon_background="#E3F2FD",
                icon_color="#1976D2",
            ),
            _help_menu_row(
                "●",
                "การถ่ายรูปให้ OCR แม่น",
                "เทคนิคการถ่ายรูปให้ได้ผลลัพธ์ที่แม่นยำ",
                HELP_TOPIC_CONFIRM_READING,
            ),
            _help_menu_row(
                "!",
                "ปัญหาที่พบบ่อย",
                "รวมปัญหาที่พบบ่อยและวิธีแก้ไข",
                HELP_TOPIC_TROUBLESHOOTING,
                icon_background="#FFF3E0",
                icon_color="#F57C00",
            ),
            _help_menu_row(
                "⚙",
                "ตั้งค่าระบบ",
                "ตั้งค่าระบบและการแจ้งเตือน",
                HELP_TOPIC_SETTINGS,
                icon_background="#EEF1F5",
                icon_color="#5F6773",
            ),
        ],
    }


def _help_recommendation_panel() -> dict:
    rows = [
        _help_menu_row("•", "อ่านค่าไม่ได้", "ตัวเลขไม่ชัดเจน", HELP_TOPIC_TROUBLESHOOTING),
        _help_menu_row("•", "ตัวเลขผิด", "ค่าที่อ่านไม่ถูกต้อง", HELP_TOPIC_CONFIRM_READING),
        _help_menu_row("•", "ส่งรายงานไม่ได้", "รายงานไม่สำเร็จ", HELP_TOPIC_LATEST_REPORT),
    ]
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "paddingAll": "12px",
        "cornerRadius": "8px",
        "borderWidth": "1px",
        "borderColor": "#C9E6D0",
        "backgroundColor": "#F6FBF7",
        "contents": [
            {
                "type": "text",
                "text": "แนะนำสำหรับคุณ",
                "size": "sm",
                "weight": "bold",
                "color": CARD_COLORS["text"],
                "wrap": True,
            },
            *rows,
        ],
    }


def _help_contact_cta() -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "md",
        "alignItems": "center",
        "paddingAll": "12px",
        "cornerRadius": "8px",
        "backgroundColor": CARD_COLORS["dark_green"],
        "action": {
            "type": "postback",
            "label": "ติดต่อแอดมิน",
            "data": build_postback_data(action=POSTBACK_SETTINGS_CONTACT_ADMIN),
            "displayText": "ติดต่อแอดมิน",
        },
        "contents": [
            _help_icon_box(
                "...",
                background_color=CARD_COLORS["white"],
                color=CARD_COLORS["dark_green"],
                size="md",
            ),
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "contents": [
                    {
                        "type": "text",
                        "text": "ติดต่อแอดมิน",
                        "size": "md",
                        "weight": "bold",
                        "color": CARD_COLORS["white"],
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": "สอบถามปัญหาการใช้งานหรือขอความช่วยเหลือ",
                        "size": "xs",
                        "color": CARD_COLORS["white"],
                        "wrap": True,
                    },
                ],
                "flex": 1,
            },
            {
                "type": "text",
                "text": ">",
                "size": "xl",
                "color": CARD_COLORS["white"],
                "align": "end",
                "flex": 0,
            },
        ],
    }


def build_help_menu_message() -> FlexMessage:
    contents = {
        "type": "bubble",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": CARD_PADDING,
            "backgroundColor": CARD_COLORS["white"],
            "contents": [
                _help_hero(),
                _help_section_header("เมนูด่วน"),
                _help_quick_grid(),
                {"type": "separator", "color": "#E0E0E0"},
                _help_section_header("หมวดหมู่ช่วยเหลือ", "ดูทั้งหมด >"),
                _help_category_list(),
                _help_recommendation_panel(),
                _help_contact_cta(),
            ],
        },
    }
    return FlexMessage(
        alt_text="Help วิธีใช้งาน",
        contents=FlexContainer.from_dict(contents),
        quick_reply=_quick_reply_from_actions(
            (
                (
                    "บันทึกมิเตอร์",
                    "postback",
                    _help_postback_data(HELP_TOPIC_START_COLLECTION),
                ),
                (
                    "ยืนยัน/แก้ OCR",
                    "postback",
                    _help_postback_data(HELP_TOPIC_CONFIRM_READING),
                ),
                (
                    "ดูสถานะ",
                    "postback",
                    build_postback_data(action=POSTBACK_SHOW_STATUS),
                ),
                (
                    "รายงานล่าสุด",
                    "postback",
                    build_postback_data(action=POSTBACK_LATEST_REPORT),
                ),
            )
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
