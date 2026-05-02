from decimal import Decimal

from app.line.messages import (
    build_confirmation_card,
    build_meter_request_message,
    build_start_collection_card,
)
from app.line.webhook import _normalize_message_payload


def _as_dict(message):
    return message.dict(by_alias=True, exclude_none=True)


def test_start_collection_flex_keeps_body_contents():
    payload = _as_dict(build_start_collection_card())

    assert payload["contents"]["type"] == "bubble"
    assert "body" in payload["contents"]
    assert "เริ่มบันทึกค่ามิเตอร์สัปดาห์นี้" in str(payload)


def test_confirmation_flex_keeps_footer_actions():
    payload = _as_dict(
        build_confirmation_card(
            meter_id="M1",
            current_value=Decimal("12508"),
            prev_value=Decimal("12000"),
            produced=Decimal("508"),
            amount=Decimal("2134"),
        )
    )

    assert payload["contents"]["type"] == "bubble"
    assert "footer" in payload["contents"]
    assert "confirm_reading" in str(payload)
    assert "edit_reading" in str(payload)
    assert "retake_photo" in str(payload)


def test_meter_request_message_has_quick_replies():
    payload = _as_dict(build_meter_request_message("M1"))

    assert payload["text"] == "กรุณาถ่ายรูปเครื่อง M1"
    assert len(payload["quickReply"]["items"]) == 11


def test_meter_request_uses_select_meter_postbacks_instead_of_m1_text_jump():
    payload = _as_dict(build_meter_request_message("M4"))
    actions = [item["action"] for item in payload["quickReply"]["items"]]

    assert not any(action["type"] == "message" and action.get("text") == "M1" for action in actions)
    assert any(
        action["type"] == "postback"
        and action["data"] == "action=select_meter&meter_id=M4"
        for action in actions
    )


def test_normalize_line_message_payload_wraps_single_message():
    message = build_meter_request_message("M1")

    payload = _normalize_message_payload(message)

    assert payload == [message]


def test_normalize_line_message_payload_accepts_mixed_list():
    message = build_meter_request_message("M1")

    payload = _normalize_message_payload(["เริ่ม", message])

    assert payload[0].text == "เริ่ม"
    assert payload[1] is message
