from __future__ import annotations

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

def _history_icon_box(
    icon: str,
    *,
    width: str = "42px",
    height: str = "42px",
    corner_radius: str = "10px",
    size: str = "lg",
) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "width": width,
        "height": height,
        "cornerRadius": corner_radius,
        "backgroundColor": CARD_COLORS["light_green"],
        "justifyContent": "center",
        "contents": [
            {
                "type": "text",
                "text": icon,
                "size": size,
                "weight": "bold",
                "align": "center",
                "color": CARD_COLORS["dark_green"],
            }
        ],
    }


def _history_menu_row(
    icon: str,
    label: str,
    action: str,
    *,
    description: str,
    **kwargs: str | int | bool | None,
) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "alignItems": "center",
        "paddingAll": "8px",
        "cornerRadius": "8px",
        "borderWidth": "1px",
        "borderColor": "#E0E0E0",
        "backgroundColor": CARD_COLORS["white"],
        "action": {
            "type": "postback",
            "label": label[:QUICK_TEXT_LIMIT],
            "data": build_postback_data(action=action, **kwargs),
            "displayText": label,
        },
        "contents": [
            _history_icon_box(icon),
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "none",
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
                        "margin": "xs",
                    },
                ],
                "flex": 1,
            },
            {
                "type": "text",
                "text": ">",
                "size": "xl",
                "color": CARD_COLORS["dark_green"],
                "align": "end",
                "flex": 0,
            },
        ],
    }


def _history_menu_rows() -> tuple[dict, ...]:
    return (
        _history_menu_row(
            "▦",
            "รอบปัจจุบัน",
            POSTBACK_HISTORY_CURRENT,
            description="ดูข้อมูลรอบที่กำลังบันทึก",
        ),
        _history_menu_row(
            "◷",
            "สัปดาห์ก่อน",
            POSTBACK_HISTORY_PREVIOUS,
            description="ดูรอบก่อนหน้าล่าสุด",
        ),
        _history_menu_row(
            "↺",
            "เลือกรอบย้อนหลัง",
            POSTBACK_HISTORY_SELECT_WEEK,
            description="เลือกรายการย้อนหลัง 1 เดือน",
        ),
        _history_menu_row(
            "▥",
            "ดูตามมิเตอร์",
            POSTBACK_HISTORY_METER,
            description="ดูประวัติรายเครื่อง",
        ),
    )


def _history_quick_actions() -> tuple[tuple[str, str, str], ...]:
    return (
        ("รอบปัจจุบัน", "postback", build_postback_data(action=POSTBACK_HISTORY_CURRENT)),
        ("สัปดาห์ก่อน", "postback", build_postback_data(action=POSTBACK_HISTORY_PREVIOUS)),
        ("เลือกรอบย้อนหลัง", "postback", build_postback_data(action=POSTBACK_HISTORY_SELECT_WEEK)),
        ("ดูตามมิเตอร์", "postback", build_postback_data(action=POSTBACK_HISTORY_METER)),
    )


def build_history_menu_message() -> FlexMessage:
    contents = {
        "type": "bubble",
        "size": "giga",
        "styles": {"footer": {"separator": True}},
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
                    "alignItems": "center",
                    "contents": [
                        {
                            "type": "box",
                            "layout": "vertical",
                            "spacing": "none",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "เลือกข้อมูลที่ต้องการดู",
                                    "weight": "bold",
                                    "size": "lg",
                                    "color": CARD_COLORS["dark_green"],
                                    "wrap": True,
                                },
                                {
                                    "type": "text",
                                    "text": "เลือกเส้นทางด้านล่างเพื่อดูข้อมูลย้อนหลัง",
                                    "size": "sm",
                                    "color": CARD_COLORS["neutral_gray"],
                                    "wrap": True,
                                    "margin": "xs",
                                },
                            ],
                            "flex": 1,
                        },
                        _history_icon_box("✓"),
                    ],
                },
                *_history_menu_rows(),
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": CARD_PADDING,
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "contents": [
                        _postback_button(
                            "รายงานล่าสุด",
                            POSTBACK_LATEST_REPORT,
                            style="primary",
                            color=CARD_COLORS["primary"],
                        ),
                        _postback_button("Help", POSTBACK_HELP),
                    ],
                }
            ],
        },
    }
    return FlexMessage(
        alt_text="ประวัติการบันทึก",
        contents=FlexContainer.from_dict(contents),
        quick_reply=_quick_reply_from_actions(_history_quick_actions()),
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


def _history_batch_list_row(summary) -> dict:
    label = summary.week or summary.batch_id
    confirmed = summary.confirmed_meter_count
    expected = summary.expected_meter_count
    try:
        is_complete = int(confirmed) >= int(expected) and int(expected) > 0
    except (TypeError, ValueError):
        is_complete = str(confirmed) == str(expected)
    count_color = CARD_COLORS["dark_green"] if is_complete else "#E53935"

    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "alignItems": "center",
        "paddingAll": "8px",
        "action": {
            "type": "postback",
            "label": label[:QUICK_TEXT_LIMIT],
            "data": build_postback_data(action=POSTBACK_HISTORY_BATCH, batch_id=summary.batch_id),
            "displayText": label,
        },
        "contents": [
            _history_icon_box("▦", width="34px", height="34px", corner_radius="8px", size="sm"),
            {
                "type": "text",
                "text": label,
                "size": "md",
                "color": CARD_COLORS["text"],
                "wrap": False,
                "flex": 4,
            },
            {
                "type": "text",
                "text": f"{confirmed}/{expected} เครื่อง",
                "size": "sm",
                "weight": "bold",
                "color": count_color,
                "align": "end",
                "wrap": False,
                "flex": 4,
            },
            {
                "type": "text",
                "text": ">",
                "size": "xl",
                "color": CARD_COLORS["dark_green"],
                "align": "end",
                "flex": 0,
            },
        ],
    }


def _history_batch_list_box(summaries: Sequence) -> dict:
    contents = []
    for index, summary in enumerate(summaries):
        if index:
            contents.append({"type": "separator", "color": "#DDE7DD"})
        contents.append(_history_batch_list_row(summary))
    return {
        "type": "box",
        "layout": "vertical",
        "cornerRadius": "12px",
        "backgroundColor": CARD_COLORS["light_green"],
        "contents": contents,
    }


def build_history_batch_list_message(summaries: Sequence) -> FlexMessage | TextMessage:
    if not summaries:
        return build_history_empty_message("ยังไม่มีประวัติย้อนหลังใน 1 เดือนนี้ครับ")

    items = [
        (
            summary.week or summary.batch_id,
            "postback",
            build_postback_data(action=POSTBACK_HISTORY_BATCH, batch_id=summary.batch_id),
        )
        for summary in summaries
    ]
    items.append(("กลับประวัติ", "postback", build_postback_data(action=POSTBACK_HISTORY)))
    contents = {
        "type": "bubble",
        "size": "mega",
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": CARD_PADDING,
            "contents": [
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "alignItems": "center",
                    "contents": [
                        {
                            "type": "text",
                            "text": "↺",
                            "size": "xl",
                            "weight": "bold",
                            "color": CARD_COLORS["dark_green"],
                            "flex": 0,
                        },
                        {
                            "type": "text",
                            "text": "ประวัติย้อนหลัง 1 เดือน",
                            "size": "lg",
                            "weight": "bold",
                            "color": CARD_COLORS["dark_green"],
                            "wrap": True,
                        },
                    ],
                },
                {"type": "separator", "color": "#D1D5DB"},
                _body_text("เลือกรอบที่ต้องการดูครับ", size="sm", color=CARD_COLORS["text"]),
                _history_batch_list_box(summaries),
            ],
        },
    }
    return FlexMessage(
        alt_text="ประวัติย้อนหลัง 1 เดือน",
        contents=FlexContainer.from_dict(contents),
        quick_reply=_quick_reply_from_actions(items),
    )
