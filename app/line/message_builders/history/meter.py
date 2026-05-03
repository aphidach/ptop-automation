from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from linebot.v3.messaging import FlexContainer, FlexMessage

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
    THAI_MONTHS_SHORT,
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

HISTORY_METER_PERIODS = (7, 30, 90)


def _meter_select_grid(
    meter_ids: Sequence[str],
    *,
    selected_meter_id: str | None = None,
) -> dict:
    meter_boxes = [
        {
            "type": "box",
            "layout": "horizontal",
            "height": "48px",
            "cornerRadius": "8px",
            "borderWidth": "1px",
            "borderColor": CARD_COLORS["dark_green"]
            if meter_id == selected_meter_id
            else "#C8E6C9",
            "backgroundColor": "#F1FAF2",
            "justifyContent": "center",
            "alignItems": "center",
            "spacing": "xs",
            "action": {
                "type": "postback",
                "label": meter_id[:QUICK_TEXT_LIMIT],
                "data": build_postback_data(action=POSTBACK_HISTORY_METER, meter_id=meter_id),
                "displayText": meter_id,
            },
            "contents": [
                {
                    "type": "text",
                    "text": "▦",
                    "size": "md",
                    "align": "end",
                    "color": CARD_COLORS["dark_green"],
                    "flex": 0,
                },
                {
                    "type": "text",
                    "text": meter_id,
                    "size": "md",
                    "weight": "bold",
                    "align": "start",
                    "color": CARD_COLORS["dark_green"],
                    "flex": 0,
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


def _history_meter_period(period_days: int | None) -> int:
    return period_days if period_days in HISTORY_METER_PERIODS else 7


def _history_meter_label(meter_id: str) -> str:
    digits = "".join(ch for ch in str(meter_id) if ch.isdigit())
    if not digits:
        return "มิเตอร์"
    return f"มิเตอร์ #{int(digits):03d}"


def _history_meter_week(row: dict | None) -> str:
    if not row:
        return "-"
    return str(row.get("week") or row.get("date") or "-")


def _history_meter_short_week(row: dict) -> str:
    week = str(row.get("week") or "").strip()
    if "-W" in week:
        return "W" + week.rsplit("-W", 1)[1]
    if week.upper().startswith("W"):
        return week.upper()
    date_value = _parse_line_datetime(row.get("date") or row.get("created_at"))
    if date_value:
        return f"{date_value.day} {THAI_MONTHS_SHORT[date_value.month - 1]}"
    return "-"


def _history_meter_updated(row: dict | None) -> str:
    if not row:
        return "-"
    parsed = _parse_line_datetime(row.get("created_at") or row.get("date"))
    return _thai_datetime(parsed) if parsed else "-"


def _history_meter_delta_percent(latest: dict, previous: dict | None) -> str:
    if not previous:
        return ""
    produced = _message_decimal(latest.get("produced_unit"))
    previous_value = _message_decimal(previous.get("current_value"))
    if previous_value == 0:
        return ""
    percent = (produced / previous_value * Decimal("100")).quantize(Decimal("0.01"))
    sign = "+" if percent >= 0 else ""
    return f"({sign}{_format_number(percent)}%)"


def _history_meter_kwh_parts(value) -> tuple[str, str]:
    return _format_number(value), "kWh"


def _history_meter_signed_kwh_parts(value) -> tuple[str, str]:
    number = _message_decimal(value)
    sign = "+" if number >= 0 else ""
    return f"{sign}{_format_number(number)}", "kWh"


def _history_meter_updated_compact(row: dict | None) -> str:
    updated = _history_meter_updated(row)
    if " " not in updated:
        return updated
    date_part, time_part = updated.rsplit(" ", 1)
    return f"{date_part}\n{time_part}"


def _history_meter_header(meter_id: str) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "alignItems": "flex-start",
        "contents": [
            {
                "type": "box",
                "layout": "vertical",
                "width": "42px",
                "height": "42px",
                "cornerRadius": "8px",
                "backgroundColor": CARD_COLORS["primary"],
                "justifyContent": "center",
                "contents": [
                    {
                        "type": "text",
                        "text": meter_id,
                        "size": "md",
                        "weight": "bold",
                        "align": "center",
                        "color": CARD_COLORS["white"],
                    }
                ],
            },
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "contents": [
                    {
                        "type": "text",
                        "text": f"ประวัติ {meter_id}",
                        "size": "lg",
                        "weight": "bold",
                        "color": CARD_COLORS["dark_green"],
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": _history_meter_label(meter_id),
                        "size": "xs",
                        "color": CARD_COLORS["neutral_gray"],
                        "wrap": True,
                    },
                ],
                "flex": 1,
            },
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "xs",
                "alignItems": "center",
                "paddingAll": "5px",
                "cornerRadius": "8px",
                "borderWidth": "1px",
                "borderColor": "#C8E6C9",
                "backgroundColor": "#F1FAF2",
                "contents": [
                    {
                        "type": "text",
                        "text": "↗",
                        "size": "xs",
                        "color": CARD_COLORS["dark_green"],
                        "flex": 0,
                    },
                    {
                        "type": "text",
                        "text": "ปกติ",
                        "size": "xs",
                        "weight": "bold",
                        "color": CARD_COLORS["dark_green"],
                        "flex": 0,
                    },
                ],
                "flex": 0,
            },
        ],
    }


def _history_meter_metric_tile(
    icon: str,
    label: str,
    value: str,
    *,
    unit: str = "kWh",
    detail: str = "",
    value_color: str = CARD_COLORS["dark_green"],
) -> dict:
    contents = [
        {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "alignItems": "center",
            "contents": [
                {
                    "type": "text",
                    "text": icon,
                    "size": "lg",
                    "color": CARD_COLORS["dark_green"],
                    "flex": 0,
                },
                {
                    "type": "text",
                    "text": label,
                    "size": "sm",
                    "color": CARD_COLORS["text"],
                    "wrap": True,
                    "flex": 1,
                },
            ],
        },
        {
            "type": "box",
            "layout": "horizontal",
            "spacing": "xs",
            "alignItems": "flex-end",
            "margin": "xs",
            "contents": [
                {
                    "type": "text",
                    "text": value,
                    "size": "xxl",
                    "weight": "bold",
                    "color": value_color,
                    "wrap": False,
                    "flex": 0,
                },
                {
                    "type": "text",
                    "text": unit,
                    "size": "md",
                    "weight": "bold",
                    "color": value_color,
                    "wrap": False,
                    "flex": 0,
                },
            ],
        },
    ]
    if detail:
        contents.append(
            {
                "type": "text",
                "text": detail,
                "size": "xs",
                "color": CARD_COLORS["neutral_gray"],
                "wrap": True,
            }
        )
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "xs",
        "contents": contents,
        "flex": 1,
    }


def _history_meter_metric_panel(latest: dict, previous: dict | None) -> dict:
    current_value, current_unit = _history_meter_kwh_parts(latest.get("current_value"))
    produced_value, produced_unit = _history_meter_signed_kwh_parts(latest.get("produced_unit"))

    return {
        "type": "box",
        "layout": "vertical",
        "cornerRadius": "8px",
        "borderWidth": "1px",
        "borderColor": "#DDE3EA",
        "backgroundColor": CARD_COLORS["white"],
        "contents": [
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "md",
                "paddingAll": "12px",
                "contents": [
                    _history_meter_metric_tile(
                        "▦",
                        "รอบปัจจุบัน",
                        current_value,
                        unit=current_unit,
                    ),
                    {"type": "separator", "color": "#DDE3EA"},
                    _history_meter_metric_tile(
                        "↗",
                        "เพิ่มขึ้น",
                        produced_value,
                        unit=produced_unit,
                        detail=_history_meter_delta_percent(latest, previous),
                    ),
                ],
            },
            {"type": "separator", "color": "#DDE3EA"},
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "paddingAll": "10px",
                "contents": [
                    _history_meter_small_stat("รอบบันทึก", _history_meter_week(latest)),
                    {"type": "separator", "color": "#DDE3EA"},
                    _history_meter_small_stat("รอบก่อนหน้า", _history_meter_week(previous)),
                    {"type": "separator", "color": "#DDE3EA"},
                    _history_meter_small_stat("อัปเดตล่าสุด", _history_meter_updated_compact(latest)),
                ],
            },
        ],
    }


def _history_meter_small_stat(label: str, value: str) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "xs",
        "contents": [
            {
                "type": "text",
                "text": label,
                "size": "xs",
                "color": CARD_COLORS["neutral_gray"],
                "wrap": True,
            },
            {
                "type": "text",
                "text": value,
                "size": "sm",
                "color": CARD_COLORS["text"],
                "wrap": True,
                "maxLines": 2,
            },
        ],
        "flex": 1,
    }


def _history_meter_period_chip(meter_id: str, active_period: int, period: int) -> dict:
    active = period == active_period
    return {
        "type": "box",
        "layout": "vertical",
        "paddingAll": "6px",
        "cornerRadius": "6px",
        "borderWidth": "1px",
        "borderColor": CARD_COLORS["primary"] if active else "#DDE3EA",
        "backgroundColor": "#F1FAF2" if active else "#F1F3F6",
        "action": {
            "type": "postback",
            "label": f"{period} วัน",
            "data": build_postback_data(
                action=POSTBACK_HISTORY_METER,
                meter_id=meter_id,
                period_days=period,
            ),
            "displayText": f"{period} วัน",
        },
        "contents": [
            {
                "type": "text",
                "text": f"{period} วัน",
                "size": "xs",
                "weight": "bold" if active else "regular",
                "color": CARD_COLORS["dark_green"] if active else CARD_COLORS["text"],
                "align": "center",
            }
        ],
        "flex": 1,
    }


def _history_meter_period_chips(meter_id: str, active_period: int) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "xs",
        "contents": [
            _history_meter_period_chip(meter_id, active_period, period)
            for period in HISTORY_METER_PERIODS
        ],
    }


def _history_meter_chart_labels(labels: Sequence[str]) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "xs",
        "contents": [
            {
                "type": "text",
                "text": label,
                "size": "xs",
                "color": CARD_COLORS["neutral_gray"],
                "align": "center",
                "flex": 1,
            }
            for label in labels
        ] or [
            {
                "type": "text",
                "text": "-",
                "size": "xs",
                "color": CARD_COLORS["neutral_gray"],
                "align": "center",
            }
        ],
    }


def _history_meter_latest_point_chart(latest_value: str, label: str) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "alignItems": "center",
        "height": "150px",
        "flex": 1,
        "contents": [
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "xs",
                "contents": [
                    {
                        "type": "text",
                        "text": "140k",
                        "size": "xs",
                        "color": CARD_COLORS["neutral_gray"],
                    },
                    {
                        "type": "text",
                        "text": "130k",
                        "size": "xs",
                        "color": CARD_COLORS["neutral_gray"],
                    },
                    {
                        "type": "text",
                        "text": "120k",
                        "size": "xs",
                        "color": CARD_COLORS["neutral_gray"],
                    },
                ],
                "flex": 0,
            },
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "paddingAll": "16px",
                "cornerRadius": "6px",
                "backgroundColor": "#F1FAF2",
                "height": "150px",
                "justifyContent": "center",
                "contents": [
                    {
                        "type": "text",
                        "text": latest_value,
                        "size": "sm",
                        "weight": "bold",
                        "color": CARD_COLORS["dark_green"],
                        "align": "center",
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": "●",
                        "size": "sm",
                        "color": CARD_COLORS["primary"],
                        "align": "center",
                    },
                    {
                        "type": "text",
                        "text": label,
                        "size": "sm",
                        "color": CARD_COLORS["neutral_gray"],
                        "align": "center",
                    },
                ],
                "flex": 1,
            },
        ],
    }


def _history_meter_sparkline_chart(labels: Sequence[str], latest_value: str, sparkline: str) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "paddingAll": "14px",
        "cornerRadius": "6px",
        "backgroundColor": "#F1FAF2",
        "height": "150px",
        "justifyContent": "center",
        "flex": 1,
        "contents": [
            {
                "type": "text",
                "text": latest_value,
                "size": "xs",
                "weight": "bold",
                "color": CARD_COLORS["dark_green"],
                "align": "end",
                "wrap": True,
            },
            {
                "type": "text",
                "text": sparkline,
                "size": "md",
                "color": CARD_COLORS["primary"],
                "align": "center",
                "wrap": True,
            },
            _history_meter_chart_labels(labels),
        ],
    }


def _history_meter_chart_panel(meter_id: str, readings: Sequence[dict], period_days: int) -> dict:
    chart_rows = list(reversed(list(readings[:6])))
    labels = [_history_meter_short_week(row) for row in chart_rows]
    values = [_message_decimal(row.get("current_value")) for row in chart_rows]
    latest_value = f"{_format_number(values[-1])} kWh" if values else "-"
    sparkline = " ━ ".join("●" for _ in chart_rows) if chart_rows else "-"
    chart_visual = (
        _history_meter_latest_point_chart(latest_value, labels[-1] if labels else "-")
        if len(chart_rows) <= 1
        else _history_meter_sparkline_chart(labels, latest_value, sparkline)
    )

    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "paddingAll": "14px",
        "cornerRadius": "8px",
        "borderWidth": "1px",
        "borderColor": "#DDE3EA",
        "backgroundColor": CARD_COLORS["white"],
        "contents": [
            {
                "type": "text",
                "text": "▮ กราฟการใช้ไฟฟ้า",
                "size": "sm",
                "weight": "bold",
                "color": CARD_COLORS["text"],
                "wrap": True,
            },
            _history_meter_period_chips(meter_id, period_days),
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "alignItems": "flex-end",
                "contents": [
                    chart_visual,
                ],
            },
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "alignItems": "center",
                "contents": [
                    {
                        "type": "text",
                        "text": "ข้อมูลรอบปัจจุบัน",
                        "size": "xs",
                        "color": CARD_COLORS["text"],
                        "wrap": True,
                        "flex": 1,
                    },
                    {
                        "type": "text",
                        "text": f"ข้อมูล ณ {_history_meter_updated(readings[0]) if readings else '-'}",
                        "size": "xs",
                        "color": CARD_COLORS["neutral_gray"],
                        "align": "end",
                        "wrap": True,
                        "flex": 2,
                    },
                ],
            },
        ],
    }


def _history_meter_footer_actions() -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "sm",
        "contents": [
            _postback_button(
                "ส่งรายงานล่าสุด",
                POSTBACK_LATEST_REPORT,
                style="primary",
                color=CARD_COLORS["primary"],
            ),
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": [
                    _postback_button("เลือกเครื่องอื่น", POSTBACK_HISTORY_METER),
                    _postback_button("กลับประวัติ", POSTBACK_HISTORY),
                ],
            },
        ],
    }


def _history_meter_quick_actions() -> tuple[tuple[str, str, str], ...]:
    return (
        ("ส่งรายงานล่าสุด", "postback", build_postback_data(action=POSTBACK_LATEST_REPORT)),
        ("เลือกเครื่องอื่น", "postback", build_postback_data(action=POSTBACK_HISTORY_METER)),
        ("กลับประวัติ", "postback", build_postback_data(action=POSTBACK_HISTORY)),
    )


def build_history_meter_select_message(meter_ids: Sequence[str] | None = None) -> FlexMessage:
    display_meter_ids = tuple(meter_ids or DEFAULT_METER_IDS)
    items = [
        (meter_id, "postback", build_postback_data(action=POSTBACK_HISTORY_METER, meter_id=meter_id))
        for meter_id in display_meter_ids
    ]
    items.append(("กลับประวัติ", "postback", build_postback_data(action=POSTBACK_HISTORY)))

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
                    "layout": "vertical",
                    "spacing": "xs",
                    "contents": [
                        {
                            "type": "text",
                            "text": "ดูตามมิเตอร์",
                            "size": "xxl",
                            "weight": "bold",
                            "color": CARD_COLORS["dark_green"],
                            "wrap": True,
                        },
                        {
                            "type": "text",
                            "text": "เลือกมิเตอร์ที่ต้องการดู",
                            "size": "sm",
                            "color": CARD_COLORS["neutral_gray"],
                            "wrap": True,
                        },
                    ],
                },
                _body_text(
                    "แตะเครื่องด้านล่างเพื่อดูประวัติรายเครื่อง",
                    size="md",
                    color=CARD_COLORS["text"],
                ),
                _meter_select_grid(display_meter_ids),
            ],
        },
        "footer": {
            "type": "box",
            "layout": "horizontal",
            "spacing": "sm",
            "paddingAll": CARD_PADDING,
            "contents": [
                _postback_button("กลับประวัติ", POSTBACK_HISTORY),
                _postback_button(
                    "รายงานล่าสุด",
                    POSTBACK_LATEST_REPORT,
                    style="primary",
                    color=CARD_COLORS["primary"],
                ),
            ],
        },
    }
    return FlexMessage(
        alt_text="ดูตามมิเตอร์",
        contents=FlexContainer.from_dict(contents),
        quick_reply=_quick_reply_from_actions(items),
    )


def build_history_meter_message(
    meter_id: str,
    readings: Sequence[dict],
    period_days: int = 7,
) -> FlexMessage:
    active_period = _history_meter_period(period_days)
    if not readings:
        return _card_shell(
            alt_text=f"ประวัติ {meter_id}",
            title=f"ประวัติ {meter_id}",
            subtitle=_history_meter_label(meter_id),
            body_contents=(
                _body_text(f"ยังไม่มีประวัติของ {meter_id} ในช่วง {active_period} วันครับ"),
                _history_meter_period_chips(meter_id, active_period),
            ),
            primary_action=_postback_button(
                "เริ่มบันทึกมิเตอร์",
                POSTBACK_START_COLLECTION,
                style="primary",
                color=CARD_COLORS["primary"],
            ),
            secondary_actions=(
                _postback_button("เลือกเครื่องอื่น", POSTBACK_HISTORY_METER),
                _postback_button("กลับประวัติ", POSTBACK_HISTORY),
            ),
            quick_actions=(
                ("เริ่มบันทึกมิเตอร์", "postback", build_postback_data(action=POSTBACK_START_COLLECTION)),
                ("เลือกเครื่องอื่น", "postback", build_postback_data(action=POSTBACK_HISTORY_METER)),
                ("กลับประวัติ", "postback", build_postback_data(action=POSTBACK_HISTORY)),
            ),
        )

    latest = readings[0]
    previous = readings[1] if len(readings) > 1 else None
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
                _history_meter_header(meter_id),
                _history_meter_metric_panel(latest, previous),
                _history_meter_chart_panel(meter_id, readings, active_period),
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": CARD_PADDING,
            "contents": [_history_meter_footer_actions()],
        },
    }
    return FlexMessage(
        alt_text=f"ประวัติ {meter_id}",
        contents=FlexContainer.from_dict(contents),
        quick_reply=_quick_reply_from_actions(_history_meter_quick_actions()),
    )
