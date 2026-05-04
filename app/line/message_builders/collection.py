from __future__ import annotations

from decimal import Decimal
from typing import Sequence

from linebot.v3.messaging import FlexMessage

from app.line.parser import (
    POSTBACK_CANCEL_COLLECTION,
    POSTBACK_CONFIRM_READING,
    POSTBACK_EDIT_READING,
    POSTBACK_FORCE_CONFIRM_READING,
    POSTBACK_REPLACE_READING,
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

from app.line.message_builders.assets import _start_collection_hero_url
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
        guidance="กดแทนที่เพื่ออัปเดตค่าเดิมในรอบนี้ หรือแก้ไข/ถ่ายใหม่",
        rows=(
            ("ค่าเดิม", _kwh_display_value(old_value)),
            ("ค่าใหม่", _kwh_display_value(new_value)),
        ),
        footer_buttons=(
            _postback_button(
                "แทนที่",
                POSTBACK_REPLACE_READING,
                meter_id=meter_id,
                style="primary",
                color=CARD_COLORS["energy_yellow"],
            ),
            _postback_button("แก้ไข", POSTBACK_EDIT_READING, meter_id=meter_id),
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
