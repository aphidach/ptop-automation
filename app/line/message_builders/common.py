from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
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


THAI_TZ = timezone(timedelta(hours=7))


THAI_MONTHS_SHORT = (
    "ม.ค.",
    "ก.พ.",
    "มี.ค.",
    "เม.ย.",
    "พ.ค.",
    "มิ.ย.",
    "ก.ค.",
    "ส.ค.",
    "ก.ย.",
    "ต.ค.",
    "พ.ย.",
    "ธ.ค.",
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


def _text_with_actions(
    text: str,
    action_items: Iterable[tuple[str, str, str]],
) -> TextMessage:
    return TextMessage(
        text=text,
        quick_reply=_quick_reply_from_actions(list(action_items)),
    )


def _parse_line_datetime(value) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        try:
            parsed = datetime.strptime(text, "%Y-%m-%d")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=THAI_TZ)
    return parsed.astimezone(THAI_TZ)


def _thai_date(value: datetime) -> str:
    return f"{value.day} {THAI_MONTHS_SHORT[value.month - 1]} {value.year + 543}"


def _thai_datetime(value: datetime) -> str:
    return f"{_thai_date(value)} {value:%H:%M}"


def _signed_kwh(value) -> str:
    number = _message_decimal(value)
    sign = "+" if number >= 0 else ""
    return f"{sign}{_format_number(number)} kWh"


def _safe_int(value) -> int:
    try:
        return int(str(value or "0").strip())
    except ValueError:
        return 0


def _message_decimal(value) -> Decimal:
    try:
        return Decimal(str(value or "0").replace(",", ""))
    except Exception:
        return Decimal("0")


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
