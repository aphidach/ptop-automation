from types import SimpleNamespace
from unittest.mock import patch
from decimal import Decimal

from app.line.messages import (
    HELP_FLOW_IMAGE_ASSETS,
    HELP_FLOW_PREVIEW_IMAGE_ASSETS,
    HELP_MENU_TOPICS,
    build_batch_complete_card,
    build_confirmation_card,
    build_duplicate_warning_card,
    build_help_flow_response,
    build_help_menu_message,
    build_history_batch_list_message,
    build_history_detail_message,
    build_history_menu_message,
    build_history_meter_select_message,
    build_history_summary_message,
    build_lower_value_warning,
    build_meter_request_message,
    build_ocr_review_message,
    build_report_import_preview_message,
    build_settings_menu_message,
    build_start_collection_card,
    build_status_card,
    build_report_summary_message,
    build_unreadable_prompt,
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


def _clear_line_card_image_env(monkeypatch):
    monkeypatch.delenv("LINE_CARD_IMAGE_BASE_URL", raising=False)
    monkeypatch.delenv("LINE_CARD_START_COLLECTION_HERO_URL", raising=False)


def test_start_collection_flex_keeps_body_contents():
    payload = _as_dict(build_start_collection_card())

    assert payload["contents"]["type"] == "bubble"
    assert "body" in payload["contents"]
    assert "เริ่มบันทึกมิเตอร์" in str(payload)
    assert "start_collection" in str(payload)
    assert "show_status" in str(payload)
    assert "cancel_collection" in str(payload)


def test_start_collection_card_uses_shell_and_https_hero(monkeypatch):
    _clear_line_card_image_env(monkeypatch)
    monkeypatch.setenv("LINE_CARD_START_COLLECTION_HERO_URL", "https://cdn.example.com/solar.png")

    payload = _as_dict(
        build_start_collection_card(
            week="รอบสัปดาห์นี้",
            expected_meter_count=6,
            next_meter_id="M1",
            confirmed_meter_count=0,
        )
    )
    rendered = str(payload)

    assert "เริ่มบันทึกมิเตอร์" in rendered
    assert "รอบสัปดาห์นี้ M1-M6" in rendered
    assert "0/6 เครื่อง" in rendered
    assert "https://cdn.example.com/solar.png" in rendered
    assert "action=start_collection" in rendered
    assert "text': '1'" in rendered


def test_start_collection_card_uses_base_https_hero_asset(monkeypatch):
    _clear_line_card_image_env(monkeypatch)
    monkeypatch.setenv("LINE_CARD_IMAGE_BASE_URL", "https://cdn.example.com/line-cards")

    payload = _as_dict(build_start_collection_card())

    assert (
        "https://cdn.example.com/line-cards/solar-meter-mascot-hero-v0.2.0.png"
        in str(payload)
    )


def test_start_collection_card_hides_empty_next_meter_and_visible_cancel(monkeypatch):
    _clear_line_card_image_env(monkeypatch)

    payload = _as_dict(build_start_collection_card(next_meter_id=None))

    assert "เครื่องถัดไป" not in str(payload["contents"]["body"])
    assert "cancel_collection" not in str(payload["contents"]["footer"])
    assert "cancel_collection" in str(payload["quickReply"])


def test_start_collection_card_omits_non_https_hero(monkeypatch):
    _clear_line_card_image_env(monkeypatch)
    monkeypatch.setenv("LINE_CARD_START_COLLECTION_HERO_URL", "http://cdn.example.com/solar.png")
    monkeypatch.setenv("LINE_CARD_IMAGE_BASE_URL", "https://cdn.example.com/line-cards")

    payload = _as_dict(build_start_collection_card())

    assert "http://cdn.example.com/solar.png" not in str(payload)
    assert "solar-meter-mascot-hero-v0.2.0.png" not in str(payload)


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


def test_warning_recovery_cards_keep_supported_actions_only():
    payloads = [
        _as_dict(build_unreadable_prompt("M2")),
        _as_dict(build_ocr_review_message("M2", Decimal("12508"), ["confidence ต่ำ"])),
        _as_dict(build_lower_value_warning("M2", Decimal("13000"), Decimal("12508"))),
        _as_dict(build_duplicate_warning_card("M2", old_value="13000", new_value="12508")),
    ]

    rendered = "\n".join(str(payload) for payload in payloads)
    assert "ตรวจสอบก่อนบันทึก" in rendered
    assert "retake_photo" in rendered
    assert "show_status" in rendered
    assert "cancel_collection" in rendered
    assert "replace_reading" not in rendered
    assert "share_report" not in rendered


def test_duplicate_warning_card_does_not_add_kwh_to_placeholder_old_value():
    payload = _as_dict(
        build_duplicate_warning_card("M2", old_value="มีข้อมูลเดิม", new_value="12508")
    )
    rendered = str(payload)

    assert "มีข้อมูลเดิม" in rendered
    assert "มีข้อมูลเดิม kWh" not in rendered
    assert "12508 kWh" in rendered


def test_batch_complete_card_has_safe_followup_actions():
    payload = _as_dict(
        build_batch_complete_card(
            batch_id="2026-W19-U1",
            week="2026-W19",
            expected_meter_count=8,
        )
    )

    rendered = str(payload)
    assert payload["altText"] == "บันทึกครบแล้ว กำลังสร้างรายงาน"
    assert "บันทึกครบแล้ว" in rendered
    assert "history_batch" in rendered
    assert "show_status" in rendered
    assert "latest_report" not in rendered


def test_meter_request_message_has_quick_replies():
    payload = _as_dict(build_meter_request_message("M1"))

    assert payload["altText"] == "ถ่ายรูปเครื่อง M1"
    assert payload["contents"]["type"] == "bubble"
    assert "ถ่ายรูป M1" in str(payload)
    assert len(payload["quickReply"]["items"]) == 11


def test_meter_request_message_uses_configured_meter_ids_and_no_stale_m8():
    payload = _as_dict(
        build_meter_request_message(
            "M3",
            meter_ids=["M1", "M2", "M3", "M4", "M5", "M6"],
        ),
    )
    rendered = str(payload)

    assert "M7" not in rendered
    assert "M8" not in rendered
    assert "M1-M8" not in rendered
    assert len(payload["quickReply"]["items"]) == 9
    assert any(
        item["action"]["type"] == "postback"
        and item["action"]["data"] == "action=select_meter&meter_id=M6"
        for item in payload["quickReply"]["items"]
    )


def test_meter_request_message_caps_configured_meter_quick_replies():
    payload = _as_dict(
        build_meter_request_message(
            "M1",
            meter_ids=[f"M{i}" for i in range(1, 12)],
        ),
    )
    actions = [item["action"] for item in payload["quickReply"]["items"]]

    assert len(payload["quickReply"]["items"]) <= 13
    assert any(action["data"] == "action=skip_meter&meter_id=M1" for action in actions)
    assert any(action["data"] == "action=show_status" for action in actions)
    assert any(action["data"] == "action=cancel_collection" for action in actions)
    assert any(action["data"] == "action=select_meter&meter_id=M1" for action in actions)


def test_meter_request_uses_select_meter_postbacks_instead_of_m1_text_jump():
    payload = _as_dict(build_meter_request_message("M4"))
    actions = [item["action"] for item in payload["quickReply"]["items"]]

    assert not any(action["type"] == "message" and action.get("text") == "M1" for action in actions)
    assert any(
        action["type"] == "postback"
        and action["data"] == "action=select_meter&meter_id=M4"
        for action in actions
    )

def test_status_card_renders_progress_actions():
    payload = _as_dict(
        build_status_card(
            meter_id="M2",
            pending="M1 = 12,500",
            progress_text="เก็บแล้ว 1/8 ขาด M2, M3",
            batch_id="2026-W19-U1",
            week="2026-W19",
            confirmed_count=1,
            total_count=8,
            missing_meter_ids=["M2", "M3", "M4", "M5", "M6", "M7", "M8"],
            next_meter="M2",
        )
    )

    assert payload["altText"] == "สถานะรอบบันทึก"
    assert "สถานะรอบบันทึก" in str(payload)
    assert "M1 = 12,500" in str(payload)
    assert "select_meter" in str(payload)
    assert "latest_report" in str(payload)


def test_status_card_uses_configured_total_count_in_meter_grid():
    payload = _as_dict(
        build_status_card(
            meter_id="M2",
            pending="",
            progress_text="เก็บแล้ว 2/6 ขาด M3-M6",
            confirmed_count=2,
            total_count=6,
            missing_meter_ids=["M3", "M4", "M5", "M6"],
            next_meter="M3",
        )
    )
    rendered = str(payload)

    assert "บันทึกแล้ว 2/6 เครื่อง" in rendered
    assert "บันทึกแล้ว 2/8 เครื่อง" not in rendered


def test_status_card_complete_state_omits_continue_action():
    payload = _as_dict(
        build_status_card(
            meter_id=None,
            pending="",
            progress_text="เก็บแล้วครบ 6/6 เครื่อง",
            confirmed_count=6,
            total_count=6,
            missing_meter_ids=[],
            next_meter=None,
        )
    )
    rendered = str(payload)

    assert "6/6 เครื่อง" in rendered
    assert "บันทึกต่อ" not in rendered
    assert "select_meter" not in rendered
    assert "latest_report" in rendered
    assert "help" in rendered


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

    assert payload["altText"] == "ประวัติการบันทึก"
    assert "ประวัติ" in str(payload)
    assert "history_current" in str(payload)
    assert "history_previous" in str(payload)
    assert "history_select_week" in str(payload)
    assert "history_meter" in str(payload)
    assert "latest_report" in str(payload)
    assert "help" in str(payload["contents"]["footer"])
    assert "help" not in str(payload["quickReply"])


def test_history_meter_select_message_is_card_with_meter_actions():
    payload = _as_dict(build_history_meter_select_message(("M1", "M2", "M3")))
    rendered = str(payload)

    assert payload["altText"] == "ดูตามมิเตอร์"
    assert "เลือกมิเตอร์ที่ต้องการดู" in rendered
    assert "action=history_meter&meter_id=M1" in rendered
    assert "action=history_meter&meter_id=M3" in rendered
    assert "action=history_meter&meter_id=M4" not in rendered
    assert "action=history" in rendered
    assert "latest_report" in rendered


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
    rendered = str(payload)

    assert payload["altText"] == "ประวัติย้อนหลัง 1 เดือน"
    assert payload["contents"]["type"] == "bubble"
    assert payload["contents"]["size"] == "mega"
    assert "ประวัติย้อนหลัง 1 เดือน" in rendered
    assert "2026-W18" in rendered
    assert "8/8 เครื่อง" in rendered
    assert "2026-W17" in rendered
    assert "7/8 เครื่อง" in rendered
    assert "history_batch" in rendered
    assert "batch_id=2026-W18-U1" in rendered
    assert "กลับประวัติ" in rendered


def test_history_summary_message_is_flex_card():
    summary = SimpleNamespace(
        batch_id="2026-W18-U1",
        week="2026-W18",
        status="reported",
        expected_meter_count=8,
        confirmed_meter_count=8,
        missing_meter_ids=[],
        produced_unit=Decimal("815113.15"),
        amount=Decimal("3423475.23"),
    )

    payload = _as_dict(build_history_summary_message("ประวัติสัปดาห์ก่อน", summary))
    rendered = str(payload)

    assert payload["altText"] == "ประวัติสัปดาห์ก่อน"
    assert "2026-W18" in rendered
    assert "815,113.15 kWh" in rendered
    assert "3,423,475.23 บาท" in rendered
    assert "action=history_batch_detail&batch_id=2026-W18-U1" in rendered
    assert "action=history" in rendered


def test_history_detail_message_uses_rich_detail_card():
    summary = SimpleNamespace(
        batch_id="2026-W18-U1",
        week="2026-W18",
        expected_meter_count=8,
        confirmed_meter_count=8,
        missing_meter_ids=[],
        date="2026-04-28",
        created_at="2026-04-28T02:00:00+07:00",
        updated_at="2026-04-28T02:29:00+07:00",
        readings=[
            {"meter_id": "M1", "current_value": "135420", "produced_unit": "375.8"},
            {"meter_id": "M2", "current_value": "250509.1", "produced_unit": "657.8"},
            {"meter_id": "M3", "current_value": "104860", "produced_unit": "880"},
            {"meter_id": "M4", "current_value": "84352", "produced_unit": "761"},
            {"meter_id": "M5", "current_value": "60601", "produced_unit": "1387"},
            {"meter_id": "M6", "current_value": "61270", "produced_unit": "1528"},
            {"meter_id": "M7", "current_value": "58196", "produced_unit": "1322"},
            {"meter_id": "M8", "current_value": "59905", "produced_unit": "1369"},
        ],
    )

    payload = _as_dict(build_history_detail_message(summary))
    rendered = str(payload)

    assert payload["altText"] == "รายละเอียดรอบ 2026-W18"
    assert payload["contents"]["size"] == "giga"
    assert "22 - 28 เม.ย. 2569" in rendered
    assert "บันทึกครบถ้วน" in rendered
    assert "M1" in rendered
    assert "135,420 kWh" in rendered
    assert "+375.8 kWh" in rendered
    assert "รวมทั้งสิ้น" in rendered
    assert "815,113.1 kWh" in rendered
    assert "เพิ่มขึ้นรวม" in rendered
    assert "+8,280.6 kWh" in rendered
    assert "เฉลี่ยต่อเครื่อง" in rendered
    assert "101,889.1 kWh" in rendered
    assert "ข้อมูลอัปเดตล่าสุด: 28 เม.ย. 2569 02:29" in rendered
    assert "action=latest_report&batch_id=2026-W18-U1" in rendered
    assert "action=history_meter" in rendered
    assert "action=start_collection" in rendered
    assert "action=history" in rendered


def test_settings_operator_menu_does_not_show_edit_actions():
    payload = _as_dict(
        build_settings_menu_message(
            is_admin=False,
            values={
                "default_rate": "4.2",
                "expected_meter_count": "8",
                "report_title": "รายงานพลังงานรายสัปดาห์",
            },
        )
    )
    rendered = str(payload)

    assert payload["altText"] == "ตั้งค่าระบบ"
    assert payload["contents"]["size"] == "mega"
    assert "Operator" in rendered
    assert "ดูได้เฉพาะข้อมูลปัจจุบัน" in rendered
    assert "ดูอัตราค่าไฟฟ้าต่อหน่วย" in rendered
    assert "4.20 บาท/kWh" in rendered
    assert "8 เครื่อง" in rendered
    assert "รายงานพลังงานรายสัปดาห์" in rendered
    assert "มิเตอร์ M1-M8" in rendered
    assert "settings_view" in rendered
    assert "settings_meters" in rendered
    assert "settings_edit_rate" not in rendered
    assert "settings_import_report" not in rendered
    assert "settings_sync_sheets" not in rendered
    assert "help" in str(payload["quickReply"])


def test_settings_admin_menu_shows_edit_actions():
    payload = _as_dict(
        build_settings_menu_message(
            is_admin=True,
            values={
                "default_rate": "4.2",
                "expected_meter_count": "8",
                "report_title": "รายงานพลังงานรายสัปดาห์",
            },
        )
    )
    rendered = str(payload)

    assert payload["altText"] == "ตั้งค่าระบบ"
    assert payload["contents"]["size"] == "mega"
    assert "Admin" in rendered
    assert "ดูค่าปัจจุบัน" in rendered
    assert "ตั้งค่าอัตราค่าไฟฟ้าต่อหน่วย" in rendered
    assert "ตั้งค่าจำนวนมิเตอร์ที่ใช้งาน" in rendered
    assert "ตั้งชื่อรายงานการผลิตไฟฟ้า" in rendered
    assert "เมนูสำหรับผู้ดูแลระบบเท่านั้น" in rendered
    assert "4.20 บาท/kWh" in rendered
    assert "settings_edit_rate" in rendered
    assert "settings_edit_expected_count" in rendered
    assert "settings_edit_report_title" in rendered
    assert "settings_sync_sheets" in rendered
    assert "settings_import_report" in rendered
    assert "settings_recipients" in str(payload["quickReply"])
    assert "settings_permissions" in str(payload["quickReply"])


def test_report_summary_card_shows_week_totals_and_navigation():
    with patch(
        "app.line.messages.build_report_data",
        return_value=SimpleNamespace(
            week="2026-W19",
            readings=[1, 2, 3, 4],
            total_produced_unit=Decimal("1234.5"),
            total_amount=Decimal("4567.89"),
        ),
    ):
        payload = _as_dict(build_report_summary_message("2026-W19-U1"))

    rendered = str(payload)
    assert payload["altText"] == "รายงานสัปดาห์ 2026-W19"
    assert "สรุปรายงานสัปดาห์" in rendered
    assert "สัปดาห์" in rendered
    reading_row = next(
        item
        for item in payload["contents"]["body"]["contents"]
        if item.get("type") == "box" and item.get("contents", [{}])[0].get("text") == "จำนวนเครื่อง"
    )
    assert reading_row["contents"][1]["text"] == "4"
    assert "1,234.5 kWh" in rendered
    assert "4,567.89 บาท" in rendered
    assert "action=latest_report&batch_id=2026-W19-U1" in rendered
    assert "action=history_batch_detail&batch_id=2026-W19-U1" in rendered
    assert "action=history" in rendered
    assert "share_report" not in rendered


def test_report_summary_missing_data_returns_card():
    with patch("app.line.messages.build_report_data", return_value=None):
        payload = _as_dict(build_report_summary_message("2026-W19-U1"))

    rendered = str(payload)
    assert payload["altText"] == "รายงานยังไม่พร้อม"
    assert "รายงานยังไม่พร้อม" in rendered
    assert "ยังไม่มีข้อมูลรายงานของรอบนี้" in rendered
    assert "2026-W19" in rendered
    assert "start_collection" in rendered
    assert "GEN 2026-W19-U1" in rendered


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
