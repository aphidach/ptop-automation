from __future__ import annotations

from typing import Sequence

from linebot.v3.messaging import FlexContainer, FlexMessage, TextMessage

from app.report.generator import build_report_data
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

def build_report_summary_message(
    batch_id: str,
    *,
    report_status: str = "พร้อมส่งรายงาน",
) -> FlexMessage | TextMessage:
    report = build_report_data(batch_id)
    if not report:
        return build_report_unavailable_message(
            batch_id=batch_id,
            reason="ยังไม่มีข้อมูลรายงานของรอบนี้",
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


def build_report_unavailable_message(
    *,
    batch_id: str | None = None,
    reason: str = "ยังสร้างรูปรายงานไม่ได้",
) -> FlexMessage:
    title = "รายงานยังไม่พร้อม"
    subtitle = _week_from_batch_id(batch_id) or batch_id or "ยังไม่มีรอบรายงาน"
    body_contents = [
        {
            "type": "text",
            "text": reason,
            "size": "sm",
            "color": CARD_COLORS["text"],
            "wrap": True,
        },
        {
            "type": "box",
            "layout": "vertical",
            "spacing": "sm",
            "paddingAll": "10px",
            "cornerRadius": "8px",
            "backgroundColor": CARD_COLORS["page_background"],
            "contents": [
                {
                    "type": "text",
                    "text": "ตรวจว่ารอบนี้มี readings ครบ แล้วลองสร้างรายงานอีกครั้ง",
                    "size": "xs",
                    "color": CARD_COLORS["neutral_gray"],
                    "wrap": True,
                }
            ],
        },
    ]

    return _card_shell(
        alt_text="รายงานยังไม่พร้อม",
        title=title,
        subtitle=subtitle,
        status_badge="ต้องตรวจข้อมูล",
        status_badge_tone="warning",
        body_contents=body_contents,
        primary_action=_postback_button(
            "เริ่มบันทึกมิเตอร์",
            POSTBACK_START_COLLECTION,
            style="primary",
            color=CARD_COLORS["primary"],
        ),
        secondary_actions=(
            _message_button("ลอง GEN", f"GEN {batch_id}" if batch_id else "GEN"),
            _postback_button("ประวัติ", POSTBACK_HISTORY),
        ),
        quick_actions=(
            ("รายงานล่าสุด", "postback", build_postback_data(action=POSTBACK_LATEST_REPORT)),
            ("Help", "postback", build_postback_data(action=POSTBACK_HELP)),
        ),
    )


def _week_from_batch_id(batch_id: str | None) -> str:
    parts = str(batch_id or "").split("-")
    if len(parts) >= 2 and parts[0].isdigit() and parts[1].upper().startswith("W"):
        return f"{parts[0]}-{parts[1].upper()}"
    return ""


def _report_import_visual_panel(*, show_ocr_badge: bool = False) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "md",
        "alignItems": "center",
        "paddingAll": "14px",
        "cornerRadius": "12px",
        "backgroundColor": "#F1FAF3",
        "contents": [
            {
                "type": "box",
                "layout": "vertical",
                "width": "76px",
                "height": "104px",
                "cornerRadius": "10px",
                "borderWidth": "2px",
                "borderColor": "#78909C",
                "backgroundColor": CARD_COLORS["white"],
                "justifyContent": "center",
                "alignItems": "center",
                "spacing": "xs",
                "contents": [
                    {
                        "type": "text",
                        "text": "▣",
                        "size": "xxl",
                        "align": "center",
                        "color": CARD_COLORS["text"],
                    },
                    {
                        "type": "text",
                        "text": "ไฟล์รูป",
                        "size": "xxs",
                        "align": "center",
                        "color": CARD_COLORS["neutral_gray"],
                    },
                ],
            },
            {
                "type": "text",
                "text": "→",
                "size": "xxl",
                "weight": "bold",
                "align": "center",
                "color": "#78909C",
                "flex": 0,
            },
            {
                "type": "box",
                "layout": "vertical",
                "height": "104px",
                "cornerRadius": "10px",
                "borderWidth": "1px",
                "borderColor": "#B0BEC5",
                "backgroundColor": "#F8FBFC",
                "contents": [
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "height": "24px",
                        "backgroundColor": "#7FB8B4",
                        "cornerRadius": "8px",
                        "contents": [
                            _report_table_cell("Data", color=CARD_COLORS["white"]),
                            _report_table_cell("M1", color=CARD_COLORS["white"]),
                            _report_table_cell("M2", color=CARD_COLORS["white"]),
                            _report_table_cell("M8", color=CARD_COLORS["white"]),
                        ],
                    },
                    _report_table_line(),
                    _report_table_line(),
                    _report_table_line(),
                    _report_table_line(),
                    _report_table_line(),
                ],
                "flex": 1,
            },
            {
                "type": "box",
                "layout": "vertical",
                "width": "58px",
                "height": "32px",
                "cornerRadius": "16px",
                "backgroundColor": CARD_COLORS["primary"] if show_ocr_badge else "#DCEFE2",
                "justifyContent": "center",
                "contents": [
                    {
                        "type": "text",
                        "text": "OCR",
                        "size": "xs",
                        "weight": "bold",
                        "align": "center",
                        "color": CARD_COLORS["white"] if show_ocr_badge else CARD_COLORS["dark_green"],
                    }
                ],
                "flex": 0,
            },
        ],
    }


def _report_table_cell(text: str, *, color: str = "#90A4AE") -> dict:
    return {
        "type": "text",
        "text": text,
        "size": "xxs",
        "align": "center",
        "gravity": "center",
        "color": color,
        "flex": 1,
    }


def _report_table_line() -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "height": "14px",
        "paddingStart": "8px",
        "paddingEnd": "8px",
        "contents": [
            _report_table_cell("—"),
            _report_table_cell("—"),
            _report_table_cell("—"),
            _report_table_cell("—"),
        ],
    }


def _report_import_metric(
    label: str,
    value: str,
    unit: str,
    *,
    icon: str,
    color: str,
) -> dict:
    return {
        "type": "box",
        "layout": "vertical",
        "spacing": "xs",
        "paddingAll": "10px",
        "cornerRadius": "10px",
        "borderWidth": "1px",
        "borderColor": "#DDE5EA",
        "backgroundColor": CARD_COLORS["white"],
        "contents": [
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "xs",
                "alignItems": "center",
                "contents": [
                    {
                        "type": "text",
                        "text": icon,
                        "size": "sm",
                        "weight": "bold",
                        "color": color,
                        "flex": 0,
                    },
                    {
                        "type": "text",
                        "text": label,
                        "size": "xs",
                        "color": CARD_COLORS["text"],
                        "wrap": True,
                    },
                ],
            },
            {
                "type": "text",
                "text": value,
                "size": "xl",
                "weight": "bold",
                "align": "center",
                "color": color,
                "margin": "xs",
            },
            {
                "type": "text",
                "text": unit,
                "size": "xxs",
                "align": "center",
                "color": CARD_COLORS["neutral_gray"],
            },
        ],
        "flex": 1,
    }


def _report_import_metrics(
    *,
    row_count: int,
    total_produced_unit,
    warning_count: int,
) -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "contents": [
            _report_import_metric(
                "อ่านได้",
                f"{row_count}/8",
                "เครื่อง",
                icon="✓",
                color=CARD_COLORS["primary"],
            ),
            _report_import_metric(
                "รวมผลิต",
                _format_number(total_produced_unit) if total_produced_unit is not None else "-",
                "kWh",
                icon="▥",
                color="#2B7DE9",
            ),
            _report_import_metric(
                "Warnings",
                str(warning_count),
                "รายการ",
                icon="!",
                color="#F59E0B",
            ),
        ],
    }


def _report_import_status_strip(text: str, *, tone: str = "success") -> dict:
    if tone == "warning":
        color = CARD_COLORS["warning_text"]
        background = "#FFF8E1"
        icon = "!"
    else:
        color = CARD_COLORS["dark_green"]
        background = CARD_COLORS["light_green"]
        icon = "✓"
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "sm",
        "alignItems": "center",
        "paddingAll": "10px",
        "cornerRadius": "12px",
        "backgroundColor": background,
        "contents": [
            {
                "type": "text",
                "text": icon,
                "size": "sm",
                "weight": "bold",
                "color": color,
                "flex": 0,
            },
            {
                "type": "text",
                "text": text,
                "size": "xs",
                "weight": "bold",
                "color": color,
                "wrap": True,
            },
        ],
    }


def _report_import_footer_note() -> dict:
    return {
        "type": "box",
        "layout": "horizontal",
        "spacing": "xs",
        "paddingAll": "8px",
        "cornerRadius": "8px",
        "backgroundColor": "#F2F6F9",
        "contents": [
            {
                "type": "text",
                "text": "รองรับไฟล์ JPG, PNG",
                "size": "xxs",
                "color": CARD_COLORS["neutral_gray"],
                "flex": 1,
            },
            {
                "type": "text",
                "text": "OCR อ่านค่ามิเตอร์ให้อัตโนมัติ",
                "size": "xxs",
                "color": CARD_COLORS["neutral_gray"],
                "align": "end",
                "flex": 1,
            },
        ],
    }


def _report_import_card(
    *,
    alt_text: str,
    subtitle: str,
    row_count: int,
    total_produced_unit,
    warning_count: int,
    status_text: str,
    status_tone: str = "success",
    primary_action: dict | None = None,
    secondary_actions: Sequence[dict] = (),
    quick_actions: Sequence[tuple[str, str, str]] = (),
) -> FlexMessage:
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
                    "spacing": "xs",
                    "contents": [
                        {
                            "type": "text",
                            "text": "นำเข้ารายงานเก่า",
                            "weight": "bold",
                            "size": "xl",
                            "color": CARD_COLORS["dark_green"],
                            "wrap": True,
                        },
                        {
                            "type": "text",
                            "text": subtitle,
                            "size": "sm",
                            "color": CARD_COLORS["neutral_gray"],
                            "wrap": True,
                        },
                    ],
                    "flex": 1,
                },
                {
                    "type": "box",
                    "layout": "vertical",
                    "width": "48px",
                    "height": "48px",
                    "cornerRadius": "12px",
                    "borderWidth": "1px",
                    "borderColor": "#CFE0F6",
                    "justifyContent": "center",
                    "contents": [
                        {
                            "type": "text",
                            "text": "↥",
                            "size": "xxl",
                            "weight": "bold",
                            "align": "center",
                            "color": "#2B7DE9",
                        }
                    ],
                },
            ],
        },
        _report_import_visual_panel(show_ocr_badge=row_count > 0),
        _report_import_metrics(
            row_count=row_count,
            total_produced_unit=total_produced_unit,
            warning_count=warning_count,
        ),
        _report_import_status_strip(status_text, tone=status_tone),
        _report_import_footer_note(),
    ]

    footer_contents: list[dict] = []
    if primary_action and secondary_actions:
        footer_contents.append(
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "contents": [primary_action, *secondary_actions[:1]],
            }
        )
    elif primary_action:
        footer_contents.append(primary_action)
    else:
        footer_contents.extend(secondary_actions[:2])

    contents = {
        "type": "bubble",
        "size": "mega",
        "styles": {"footer": {"separator": True}},
        "body": {
            "type": "box",
            "layout": "vertical",
            "spacing": "md",
            "paddingAll": CARD_PADDING,
            "contents": body_contents,
        },
    }
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


def build_report_import_prompt_message() -> FlexMessage:
    return _report_import_card(
        alt_text="นำเข้ารายงานเก่า",
        subtitle="ส่งรูปรายงานเก่า เพื่อดึงข้อมูลด้วย OCR",
        row_count=0,
        total_produced_unit=None,
        warning_count=0,
        status_text="ส่งรูปภาพในแชตนี้ แล้วระบบจะอ่านตารางให้ตรวจสอบ",
        status_tone="success",
        secondary_actions=(
            _postback_button("ยกเลิก", POSTBACK_CANCEL_IMPORT_REPORT),
            _postback_button("กลับตั้งค่า", POSTBACK_SETTINGS),
        ),
        quick_actions=(
            ("ยกเลิก", "postback", build_postback_data(action=POSTBACK_CANCEL_IMPORT_REPORT)),
            ("กลับตั้งค่า", "postback", build_postback_data(action=POSTBACK_SETTINGS)),
        ),
    )


def build_report_import_preview_message(pending) -> FlexMessage:
    row_count = len(pending.rows)
    warning_count = len(pending.warnings or ()) + len(pending.errors or ())
    can_confirm = _can_confirm_report_import(pending)
    if pending.duplicate:
        status_text = f"พบข้อมูลรอบ {pending.week or pending.batch_id or '-'} อยู่แล้ว"
        status_tone = "warning"
    elif pending.errors:
        status_text = pending.errors[0]
        status_tone = "warning"
    elif pending.warnings:
        status_text = pending.warnings[0]
        status_tone = "warning"
    else:
        status_text = f"ความแม่นยำ OCR พร้อมตรวจสอบ • ตรวจครบ {row_count} เครื่อง"
        status_tone = "success"

    quick_actions: list[tuple[str, str, str]] = []
    primary_action = None
    if can_confirm:
        primary_action = _postback_button(
            "ยืนยันนำเข้า",
            POSTBACK_CONFIRM_IMPORT_REPORT,
            style="primary",
            color=CARD_COLORS["primary"],
        )
        quick_actions.append(
            (
                "ยืนยันนำเข้า",
                "postback",
                build_postback_data(action=POSTBACK_CONFIRM_IMPORT_REPORT),
            )
        )
    quick_actions.extend(
        [
            ("ยกเลิก", "postback", build_postback_data(action=POSTBACK_CANCEL_IMPORT_REPORT)),
            ("กลับตั้งค่า", "postback", build_postback_data(action=POSTBACK_SETTINGS)),
        ]
    )

    return _report_import_card(
        alt_text="ตรวจสอบรายงานก่อนนำเข้า",
        subtitle=f"รอบ {pending.week or '-'} • วันที่ {pending.date or '-'}",
        row_count=row_count,
        total_produced_unit=pending.total_produced_unit,
        warning_count=warning_count,
        status_text=status_text,
        status_tone=status_tone,
        primary_action=primary_action,
        secondary_actions=(
            _postback_button("ยกเลิก", POSTBACK_CANCEL_IMPORT_REPORT),
        ),
        quick_actions=tuple(quick_actions),
    )


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
