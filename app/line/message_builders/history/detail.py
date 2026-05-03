from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

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
    detail_rows = [
        _history_detail_meter_row(meter_id, by_meter.get(meter_id))
        for meter_id in _history_detail_meter_ids(summary)
    ]

    contents = {
        "type": "bubble",
        "size": "giga",
        "styles": {"footer": {"separator": False}},
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": "20px",
            "contents": [
                _history_detail_header(
                    week,
                    _history_detail_date_range(getattr(summary, "date", "")),
                ),
                _history_detail_progress_panel(summary),
                {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": detail_rows,
                },
                _history_detail_totals_panel(summary),
            ],
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "20px",
            "contents": [
                _postback_button(
                    "ส่งรูปรายงาน",
                    POSTBACK_LATEST_REPORT,
                    batch_id=summary.batch_id,
                    style="primary",
                    color=CARD_COLORS["primary"],
                ),
                {
                    "type": "box",
                    "layout": "horizontal",
                    "spacing": "sm",
                    "contents": [
                        _postback_button("ดูตามมิเตอร์", POSTBACK_HISTORY_METER),
                        _postback_button("ประวัติ", POSTBACK_HISTORY),
                    ],
                },
                {
                    "type": "separator",
                    "margin": "sm",
                    "color": "#E5E7EB",
                },
                _history_detail_footer_meta(summary),
            ],
        },
    }

    return FlexMessage(
        alt_text=f"รายละเอียดรอบ {week}",
        contents=FlexContainer.from_dict(contents),
        quick_reply=_quick_reply_from_actions(
            (
                ("ส่งรูปรายงาน", "postback", build_postback_data(action=POSTBACK_LATEST_REPORT, batch_id=summary.batch_id)),
                ("ดูตามมิเตอร์", "postback", build_postback_data(action=POSTBACK_HISTORY_METER)),
                ("บันทึกต่อ", "postback", build_postback_data(action=POSTBACK_START_COLLECTION)),
                ("กลับประวัติ", "postback", build_postback_data(action=POSTBACK_HISTORY)),
            )
        ),
    )


def _history_detail_header(week: str, date_range: str) -> dict:
    return {
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
                        "text": "รายละเอียดรอบ",
                        "weight": "bold",
                        "size": "xl",
                        "color": CARD_COLORS["dark_green"],
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": week,
                        "size": "sm",
                        "color": CARD_COLORS["neutral_gray"],
                        "margin": "xs",
                    },
                ],
                "flex": 5,
            },
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "alignItems": "center",
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "width": "28px",
                        "height": "28px",
                        "cornerRadius": "6px",
                        "backgroundColor": CARD_COLORS["light_green"],
                        "justifyContent": "center",
                        "contents": [
                            {
                                "type": "text",
                                "text": "□",
                                "size": "lg",
                                "weight": "bold",
                                "align": "center",
                                "color": CARD_COLORS["dark_green"],
                            }
                        ],
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "spacing": "none",
                        "contents": [
                            {
                                "type": "text",
                                "text": "รอบนี้",
                                "size": "sm",
                                "color": CARD_COLORS["text"],
                                "wrap": True,
                            },
                            {
                                "type": "text",
                                "text": date_range,
                                "size": "xs",
                                "color": CARD_COLORS["neutral_gray"],
                                "wrap": True,
                                "margin": "xs",
                            },
                        ],
                    },
                ],
                "flex": 4,
            },
        ],
    }


def _history_detail_progress_panel(summary) -> dict:
    expected = _safe_int(getattr(summary, "expected_meter_count", 0))
    confirmed = _safe_int(getattr(summary, "confirmed_meter_count", 0))
    missing_ids = getattr(summary, "missing_meter_ids", ()) or ()
    missing_count = len(missing_ids) if missing_ids else max(expected - confirmed, 0)
    is_complete = expected > 0 and missing_count <= 0 and confirmed >= expected
    tone_color = CARD_COLORS["dark_green"] if is_complete else CARD_COLORS["warning_text"]
    background = "#F1FAF2" if is_complete else "#FFF8E1"
    border = "#B7DDBA" if is_complete else "#FFE082"
    title = f"{confirmed}/{expected} เครื่อง" if expected else f"{confirmed} เครื่อง"
    subtitle = "บันทึกครบถ้วน" if is_complete else f"ยังขาด {missing_count} เครื่อง"

    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "md",
        "alignItems": "center",
        "justifyContent": "center",
        "paddingAll": "12px",
        "cornerRadius": "10px",
        "backgroundColor": background,
        "borderColor": border,
        "borderWidth": "1px",
        "contents": [
            {
                "type": "box",
                "layout": "vertical",
                "width": "36px",
                "height": "36px",
                "cornerRadius": "18px",
                "backgroundColor": tone_color,
                "justifyContent": "center",
                "contents": [
                    {
                        "type": "text",
                        "text": "✓" if is_complete else "!",
                        "size": "xl",
                        "weight": "bold",
                        "align": "center",
                        "color": CARD_COLORS["white"],
                    }
                ],
            },
            {
                "type": "box",
                "layout": "vertical",
                "spacing": "none",
                "contents": [
                    {
                        "type": "text",
                        "text": title,
                        "size": "lg",
                        "weight": "bold",
                        "color": tone_color,
                        "wrap": True,
                    },
                    {
                        "type": "text",
                        "text": subtitle,
                        "size": "sm",
                        "color": tone_color,
                        "margin": "xs",
                        "wrap": True,
                    },
                ],
            },
        ],
    }


def _history_detail_meter_ids(summary) -> tuple[str, ...]:
    expected = _safe_int(getattr(summary, "expected_meter_count", len(DEFAULT_METER_IDS)))
    if expected <= 0:
        return DEFAULT_METER_IDS
    return DEFAULT_METER_IDS[: min(expected, len(DEFAULT_METER_IDS))]


def _history_detail_meter_row(meter_id: str, row: dict | None) -> dict:
    has_data = bool(row)
    current = f"{_format_number(row.get('current_value', '0'))} kWh" if row else "ยังไม่มีข้อมูล"
    produced = _signed_kwh(row.get("produced_unit", "0")) if row else "-"
    value_color = CARD_COLORS["text"] if has_data else CARD_COLORS["neutral_gray"]
    produced_color = CARD_COLORS["dark_green"] if has_data else CARD_COLORS["neutral_gray"]

    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "md",
        "alignItems": "center",
        "paddingAll": "8px",
        "cornerRadius": "8px",
        "borderColor": "#E5E7EB",
        "borderWidth": "1px",
        "contents": [
            {
                "type": "text",
                "text": meter_id,
                "size": "md",
                "weight": "bold",
                "color": CARD_COLORS["dark_green"],
                "flex": 1,
            },
            {
                "type": "text",
                "text": current,
                "size": "sm",
                "weight": "bold",
                "color": value_color,
                "align": "center",
                "wrap": True,
                "flex": 4,
            },
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "xs",
                "alignItems": "center",
                "justifyContent": "flex-end",
                "flex": 3,
                "contents": [
                    {
                        "type": "box",
                        "layout": "vertical",
                        "width": "18px",
                        "height": "18px",
                        "cornerRadius": "9px",
                        "backgroundColor": produced_color,
                        "justifyContent": "center",
                        "contents": [
                            {
                                "type": "text",
                                "text": "↑",
                                "size": "xs",
                                "weight": "bold",
                                "align": "center",
                                "color": CARD_COLORS["white"],
                            }
                        ],
                    },
                    {
                        "type": "text",
                        "text": produced,
                        "size": "sm",
                        "weight": "bold",
                        "color": produced_color,
                        "align": "end",
                        "wrap": True,
                    },
                ],
            },
        ],
    }


def _history_detail_totals_panel(summary) -> dict:
    readings = getattr(summary, "readings", ()) or ()
    expected = _safe_int(getattr(summary, "expected_meter_count", 0))
    total_current = sum((_message_decimal(row.get("current_value")) for row in readings), Decimal("0"))
    total_produced = sum((_message_decimal(row.get("produced_unit")) for row in readings), Decimal("0"))
    average_current = (total_current / Decimal(expected)).quantize(Decimal("0.1")) if expected else Decimal("0")

    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "paddingAll": "10px",
        "cornerRadius": "10px",
        "borderColor": "#D6DEE6",
        "borderWidth": "1px",
        "contents": [
            _history_detail_total_tile("▮", "รวมทั้งสิ้น", f"{_format_number(total_current)} kWh", "#2D7DCB"),
            {"type": "separator", "color": "#D6DEE6"},
            _history_detail_total_tile("↗", "เพิ่มขึ้นรวม", _signed_kwh(total_produced), CARD_COLORS["dark_green"]),
            {"type": "separator", "color": "#D6DEE6"},
            _history_detail_total_tile("↗", "เฉลี่ยต่อเครื่อง", f"{_format_number(average_current)} kWh", "#D98A00"),
        ],
    }


def _history_detail_total_tile(icon: str, label: str, value: str, color: str) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "xs",
        "alignItems": "center",
        "contents": [
            {
                "type": "text",
                "text": icon,
                "size": "md",
                "weight": "bold",
                "color": color,
                "align": "center",
            },
            {
                "type": "text",
                "text": label,
                "size": "xs",
                "color": CARD_COLORS["text"],
                "align": "center",
                "wrap": True,
            },
            {
                "type": "text",
                "text": value,
                "size": "sm",
                "weight": "bold",
                "color": color,
                "align": "center",
                "wrap": True,
            },
        ],
        "flex": 1,
    }


def _history_detail_footer_meta(summary) -> dict:
    updated = _history_detail_updated_display(summary)
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "contents": [
            {
                "type": "text",
                "text": f"ข้อมูลอัปเดตล่าสุด: {updated}",
                "size": "xs",
                "color": CARD_COLORS["neutral_gray"],
                "wrap": True,
                "flex": 5,
            },
            {
                "type": "text",
                "text": "P'top Automation",
                "size": "xs",
                "color": CARD_COLORS["neutral_gray"],
                "align": "end",
                "wrap": True,
                "flex": 3,
            },
        ],
    }


def _history_detail_date_range(date_text: str) -> str:
    end = _parse_line_datetime(date_text)
    if not end:
        return "-"
    start = end - timedelta(days=6)
    buddhist_year = end.year + 543
    if start.year != end.year:
        return f"{_thai_date(start)} - {_thai_date(end)}"
    if start.month == end.month:
        return f"{start.day} - {end.day} {THAI_MONTHS_SHORT[end.month - 1]} {buddhist_year}"
    return (
        f"{start.day} {THAI_MONTHS_SHORT[start.month - 1]} - "
        f"{end.day} {THAI_MONTHS_SHORT[end.month - 1]} {buddhist_year}"
    )


def _history_detail_updated_display(summary) -> str:
    for value in (getattr(summary, "updated_at", ""), getattr(summary, "created_at", "")):
        parsed = _parse_line_datetime(value)
        if parsed:
            return _thai_datetime(parsed)

    reading_dates = [
        parsed
        for parsed in (_parse_line_datetime(row.get("created_at")) for row in getattr(summary, "readings", ()) or ())
        if parsed
    ]
    if reading_dates:
        return _thai_datetime(max(reading_dates))
    return "-"
