from decimal import Decimal

from app.line.messages import (
    HELP_FLOW_IMAGE_ASSETS,
    HELP_FLOW_PREVIEW_IMAGE_ASSETS,
    HELP_MENU_TOPICS,
    build_confirmation_card,
    build_help_flow_response,
    build_help_menu_message,
    build_history_batch_list_message,
    build_history_menu_message,
    build_meter_request_message,
    build_report_import_preview_message,
    build_settings_menu_message,
    build_start_collection_card,
)
from app.line.webhook import _normalize_message_payload
from app.services.session_service import PendingReportImport


def _as_dict(message):
    return message.dict(by_alias=True, exclude_none=True)


def _clear_help_image_env(monkeypatch):
    for topic in HELP_MENU_TOPICS:
        monkeypatch.delenv(f"HELP_FLOW_IMAGE_{topic.upper()}_URL", raising=False)
        monkeypatch.delenv(f"HELP_FLOW_IMAGE_{topic.upper()}_PREVIEW_URL", raising=False)
    monkeypatch.delenv("HELP_FLOW_IMAGE_BASE_URL", raising=False)
    monkeypatch.delenv("HELP_FLOW_IMAGE_PREVIEW_BASE_URL", raising=False)


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


def test_help_menu_has_topic_quick_replies():
    payload = _as_dict(build_help_menu_message())

    assert payload["text"] == "ต้องการดูวิธีใช้งานส่วนไหนครับ?"
    assert len(payload["quickReply"]["items"]) <= 13
    assert "action=help_flow&topic=start_collection" in str(payload)
    assert "action=help_flow&topic=confirm_reading" in str(payload)
    assert "action=help_flow&topic=latest_report" in str(payload)
    assert "action=help_flow&topic=settings_admin" in str(payload)
    assert "action=help_flow&topic=troubleshooting" in str(payload)
    assert "action=help_flow&topic=text_commands" in str(payload)
    assert "action=help_flow&topic=contact_admin" in str(payload)


def test_help_flow_without_image_url_returns_text_fallback(monkeypatch):
    _clear_help_image_env(monkeypatch)

    payload = build_help_flow_response("start_collection")

    assert payload.text.startswith("วิธีเริ่มบันทึกค่ามิเตอร์")


def test_help_flow_with_per_topic_https_image_urls_returns_image_and_text(monkeypatch):
    _clear_help_image_env(monkeypatch)
    monkeypatch.setenv("HELP_FLOW_IMAGE_START_COLLECTION_URL", "https://example.com/help/start.png")
    monkeypatch.setenv(
        "HELP_FLOW_IMAGE_START_COLLECTION_PREVIEW_URL",
        "https://example.com/help/start-preview.jpg",
    )

    payload = build_help_flow_response("start_collection")

    assert len(payload) == 2
    image_payload = _as_dict(payload[0])
    assert image_payload["originalContentUrl"] == "https://example.com/help/start.png"
    assert image_payload["previewImageUrl"] == "https://example.com/help/start-preview.jpg"
    assert payload[1].text.startswith("วิธีเริ่มบันทึกค่ามิเตอร์")


def test_help_flow_with_base_https_image_urls_uses_ai_board_assets(monkeypatch):
    _clear_help_image_env(monkeypatch)
    monkeypatch.setenv("HELP_FLOW_IMAGE_BASE_URL", "https://cdn.example.com/help/original")
    monkeypatch.setenv("HELP_FLOW_IMAGE_PREVIEW_BASE_URL", "https://img.example.com/help/preview")

    payload = build_help_flow_response("settings_admin")

    assert len(payload) == 2
    image_payload = _as_dict(payload[0])
    assert image_payload["originalContentUrl"] == (
        "https://cdn.example.com/help/original/settings-admin-board-ai.png"
    )
    assert image_payload["previewImageUrl"] == (
        "https://img.example.com/help/preview/settings-admin-board-ai-preview.jpg"
    )
    assert payload[1].text.startswith("วิธีจัดการการตั้งค่า")


def test_help_flow_requires_explicit_https_preview_url(monkeypatch):
    _clear_help_image_env(monkeypatch)
    monkeypatch.setenv("HELP_FLOW_IMAGE_START_COLLECTION_URL", "https://example.com/help/start.png")

    payload = build_help_flow_response("start_collection")

    assert payload.text.startswith("วิธีเริ่มบันทึกค่ามิเตอร์")


def test_help_flow_rejects_non_https_preview_url(monkeypatch):
    _clear_help_image_env(monkeypatch)
    monkeypatch.setenv("HELP_FLOW_IMAGE_START_COLLECTION_URL", "https://example.com/help/start.png")
    monkeypatch.setenv("HELP_FLOW_IMAGE_START_COLLECTION_PREVIEW_URL", "http://example.com/help/start.jpg")

    payload = build_help_flow_response("start_collection")

    assert payload.text.startswith("วิธีเริ่มบันทึกค่ามิเตอร์")


def test_help_flow_image_assets_use_ai_board_filenames():
    assert HELP_FLOW_IMAGE_ASSETS == {
        "start_collection": "start-collection-board-ai.png",
        "confirm_reading": "confirm-reading-board-ai.png",
        "latest_report": "latest-report-board-ai.png",
        "history": "history-board-ai.png",
        "settings": "settings-board-ai.png",
        "settings_admin": "settings-admin-board-ai.png",
        "import_report": "import-report-board-ai.png",
        "troubleshooting": "troubleshooting-board-ai.png",
        "text_commands": "text-commands-board-ai.png",
    }
    assert HELP_FLOW_PREVIEW_IMAGE_ASSETS["troubleshooting"] == (
        "troubleshooting-board-ai-preview.jpg"
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

def test_history_menu_has_usable_actions():
    payload = _as_dict(build_history_menu_message())

    assert "ประวัติการบันทึกมิเตอร์" in payload["text"]
    assert "history_current" in str(payload)
    assert "history_select_week" in str(payload)
    assert "history_meter" in str(payload)
    assert "latest_report" in str(payload)

def test_history_batch_list_shows_recent_weeks():
    summaries = [
        type("Summary", (), {
            "batch_id": "2026-W18-U1",
            "week": "2026-W18",
            "confirmed_meter_count": 8,
            "expected_meter_count": 8,
        })(),
        type("Summary", (), {
            "batch_id": "2026-W17-U1",
            "week": "2026-W17",
            "confirmed_meter_count": 7,
            "expected_meter_count": 8,
        })(),
    ]

    payload = _as_dict(build_history_batch_list_message(summaries))

    assert "ประวัติย้อนหลัง 1 เดือน" in payload["text"]
    assert "2026-W18: 8/8" in payload["text"]
    assert "2026-W17: 7/8" in payload["text"]
    assert "history_batch" in str(payload)
    assert "batch_id=2026-W18-U1" in str(payload)

def test_settings_operator_menu_does_not_show_edit_actions():
    payload = _as_dict(build_settings_menu_message(is_admin=False))

    assert "การแก้ไขต้องใช้สิทธิ์ผู้ดูแลระบบ" in payload["text"]
    assert "settings_view" in str(payload)
    assert "settings_edit_rate" not in str(payload)
    assert "settings_import_report" not in str(payload)

def test_settings_admin_menu_shows_edit_actions():
    payload = _as_dict(build_settings_menu_message(is_admin=True))

    assert "เลือกสิ่งที่ต้องการจัดการ" in payload["text"]
    assert "settings_edit_rate" in str(payload)
    assert "settings_edit_report_title" in str(payload)
    assert "settings_import_report" in str(payload)

def test_report_import_preview_has_confirm_and_cancel_when_valid():
    pending = PendingReportImport(
        batch_id="2026-W18-U1",
        week="2026-W18",
        date="2026-04-27",
        rows=[{"meter_id": f"M{i}"} for i in range(1, 9)],
        total_produced_unit=Decimal("9456.9"),
        total_amount=Decimal("37262.7"),
    )

    payload = _as_dict(build_report_import_preview_message(pending))

    assert "ตรวจสอบรายงานก่อนนำเข้า" in payload["text"]
    assert "2026-W18" in payload["text"]
    assert "confirm_import_report" in str(payload)
    assert "cancel_import_report" in str(payload)

def test_report_import_preview_hides_confirm_when_invalid():
    pending = PendingReportImport(
        batch_id="2026-W18-U1",
        week="2026-W18",
        date="2026-04-27",
        rows=[{"meter_id": f"M{i}"} for i in range(1, 8)],
        total_produced_unit=Decimal("7410"),
        total_amount=Decimal("31122"),
        errors=["อ่านแถวได้ 7/8 แถว"],
    )

    payload = _as_dict(build_report_import_preview_message(pending))

    assert "ข้อผิดพลาด" in payload["text"]
    assert "confirm_import_report" not in str(payload)
    assert "cancel_import_report" in str(payload)
