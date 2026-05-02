from unittest.mock import Mock, patch
from types import SimpleNamespace

import pytest

from decimal import Decimal
from starlette.requests import ClientDisconnect

from app.line.parser import METER_VALUE, ParsedCommand, GEN, HELP, REPORT, STATUS, CANCEL, METER, OK, UNKNOWN
from app.line.webhook import (
    _build_reply,
    _build_status_message,
    _coerce_manual_value_command,
    handle_webhook,
    _push_to,
    _reply_to,
    _resolve_batch_id,
)
from app.services.session_service import (
    COLLECTION_WAITING_MANUAL_VALUE,
    set_batch_id,
    set_collection_current_meter,
    set_collection_state,
    set_latest_meter,
    set_pending_confirmation,
)


@pytest.fixture(autouse=True)
def _clean_sessions():
    from app.services import session_service
    session_service._store = session_service.InMemorySessionStore()
    with patch("app.services.confirmation_service.get_latest_pending_confirmation", return_value=None):
        yield
    session_service._store = session_service.InMemorySessionStore()


def test_gen_without_batch_returns_no_data_message():
    reply = _build_reply(ParsedCommand(type=GEN), "U1")

    assert "ยังไม่มีข้อมูลรอบนี้" in reply


def test_gen_schedules_image_send_for_current_batch():
    set_batch_id("U1", "2026-W19-U1")

    with patch("app.line.webhook.send_report", new=Mock(return_value="send-report-task")) as mock_send_report, \
         patch("app.line.webhook.asyncio.create_task") as mock_create_task:
        reply = _build_reply(ParsedCommand(type=GEN), "U1")

    mock_send_report.assert_called_once_with("2026-W19-U1", "U1")
    mock_create_task.assert_called_once_with("send-report-task")
    assert "กำลังส่งรูปรายงาน" in reply


def test_gen_with_week_ref_schedules_image_send_for_source_week():
    with patch("app.line.webhook.send_report", new=Mock(return_value="send-report-task")) as mock_send_report, \
         patch("app.line.webhook.asyncio.create_task") as mock_create_task:
        reply = _build_reply(ParsedCommand(type=GEN, batch_id="2026-w18"), "U1")

    mock_send_report.assert_called_once_with("2026-W18-U1", "U1")
    mock_create_task.assert_called_once_with("send-report-task")
    assert "กำลังส่งรูปรายงาน" in reply


def test_gen_with_batch_id_schedules_image_send_for_that_batch():
    with patch("app.line.webhook.send_report", new=Mock(return_value="send-report-task")) as mock_send_report, \
         patch("app.line.webhook.asyncio.create_task") as mock_create_task:
        reply = _build_reply(ParsedCommand(type=GEN, batch_id="2026-W18-UabcDef"), "U1")

    mock_send_report.assert_called_once_with("2026-W18-UabcDef", "U1")
    mock_create_task.assert_called_once_with("send-report-task")
    assert "กำลังส่งรูปรายงาน" in reply


def test_resolve_batch_id_uses_current_session_when_empty():
    set_batch_id("U1", "2026-W19-U1")

    assert _resolve_batch_id(None, "U1") == "2026-W19-U1"


def test_resolve_batch_id_converts_week_ref_to_source_batch_id():
    assert _resolve_batch_id("2026-w18", "U1") == "2026-W18-U1"


def test_resolve_batch_id_preserves_full_batch_id_case():
    assert _resolve_batch_id("2026-W18-UabcDef", "U1") == "2026-W18-UabcDef"


def test_report_without_batch_returns_no_data_message():
    reply = _build_reply(ParsedCommand(type=REPORT), "U1")

    assert "ยังไม่มีข้อมูลรอบนี้" in reply


def test_report_schedules_image_send_for_current_batch():
    set_batch_id("U1", "2026-W19-U1")

    with patch("app.line.webhook.send_report", new=Mock(return_value="send-report-task")) as mock_send_report, \
         patch("app.line.webhook.asyncio.create_task") as mock_create_task:
        reply = _build_reply(ParsedCommand(type=REPORT), "U1")

    mock_send_report.assert_called_once_with("2026-W19-U1", "U1")
    mock_create_task.assert_called_once_with("send-report-task")
    assert "กำลังส่งรูปรายงาน" in reply


def test_report_with_batch_id_schedules_image_send_for_that_batch():
    with patch("app.line.webhook.send_report", new=Mock(return_value="send-report-task")) as mock_send_report, \
         patch("app.line.webhook.asyncio.create_task") as mock_create_task:
        reply = _build_reply(
            ParsedCommand(type=REPORT, batch_id="2026-W18-U08585bd3f4116f311ae320cab4e9e1b6"),
            "U1",
        )

    mock_send_report.assert_called_once_with(
        "2026-W18-U08585bd3f4116f311ae320cab4e9e1b6",
        "U1",
    )
    mock_create_task.assert_called_once_with("send-report-task")
    assert "กำลังส่งรูปรายงาน" in reply


def test_help_includes_all_commands():
    reply = _build_reply(ParsedCommand(type=HELP), "U1")

    assert "M1" in reply
    assert "OK" in reply
    assert "CANCEL" in reply
    assert "STATUS" in reply
    assert "GEN" in reply
    assert "REPORT" in reply
    assert "HELP" in reply


def test_status_no_data():
    reply = _build_status_message("U1")

    assert "ยังไม่มีข้อมูลรอบนี้" in reply


def test_status_shows_current_meter():
    set_latest_meter("U1", "M3")

    reply = _build_status_message("U1")

    assert "มิเตอร์ปัจจุบัน: M3" in reply


def test_status_shows_pending_confirmation():
    set_pending_confirmation(
        source_id="U1",
        meter_id="M1",
        ocr_value=Decimal("12500"),
        batch_id="2026-W19-U1",
        created_at=0,
    )

    reply = _build_status_message("U1")

    assert "รอยืนยัน: M1 = 12,500" in reply


def test_status_shows_pending_confirmation_from_sheet_fallback():
    with patch(
        "app.services.confirmation_service.get_latest_pending_confirmation",
        return_value={
            "confirmation_id": "cnf_sheet",
            "line_source_id": "U1",
            "meter_id": "M1",
            "batch_id": "2026-W19-U1",
            "image_message_id": "msg1",
            "ocr_value": "12500",
            "ocr_raw_text": "12,500",
            "status": "pending",
            "expires_at": "200",
            "created_at": "100",
        },
    ):
        reply = _build_status_message("U1")

    assert "รอยืนยัน: M1 = 12,500" in reply


def test_status_shows_batch_progress():
    set_batch_id("U1", "2026-W19-U1")

    with patch("app.line.webhook.build_progress_message", return_value="เก็บแล้ว 3/8 ขาด M4, M5, M6, M7, M8"):
        reply = _build_status_message("U1")

    assert "เก็บแล้ว 3/8" in reply


def test_status_shows_meter_and_progress():
    set_latest_meter("U1", "M3")
    set_batch_id("U1", "2026-W19-U1")

    with patch("app.line.webhook.build_progress_message", return_value="เก็บแล้ว 3/8 ขาด M4, M5, M6, M7, M8"):
        reply = _build_status_message("U1")

    assert "มิเตอร์ปัจจุบัน: M3" in reply
    assert "เก็บแล้ว 3/8" in reply


def test_cancel_no_pending():
    reply = _build_reply(ParsedCommand(type=CANCEL), "U1")

    assert "ไม่มีค่าที่รอยืนยัน" in reply


def test_cancel_with_pending():
    set_pending_confirmation(
        source_id="U1",
        meter_id="M1",
        ocr_value=Decimal("12500"),
        batch_id="2026-W19-U1",
        created_at=0,
    )

    reply = _build_reply(ParsedCommand(type=CANCEL), "U1")

    assert "ยกเลิก M1" in reply


def test_status_via_build_reply():
    set_latest_meter("U1", "M2")

    reply = _build_reply(ParsedCommand(type=STATUS), "U1")

    assert "มิเตอร์ปัจจุบัน: M2" in reply


def test_manual_value_state_accepts_bare_number_for_current_meter():
    set_collection_state("U1", COLLECTION_WAITING_MANUAL_VALUE)
    set_collection_current_meter("U1", "M4")

    cmd = _coerce_manual_value_command(ParsedCommand(type=UNKNOWN, raw="12,508"), "12,508", "U1")

    assert cmd.type == METER_VALUE
    assert cmd.meter_id == "M4"
    assert cmd.value == Decimal("12508")


@pytest.mark.anyio
async def test_reply_to_accepts_sync_line_sdk_response():
    class SyncLineApi:
        def __init__(self):
            self.request = None

        def reply_message(self, request):
            self.request = request
            return object()

    api = SyncLineApi()
    with patch("app.line.webhook._messaging_api", api), \
         patch("app.line.webhook.logger.exception") as mock_log_exception:
        await _reply_to("reply-token", "hello")

    assert api.request.reply_token == "reply-token"
    assert api.request.messages[0].text == "hello"
    mock_log_exception.assert_not_called()


@pytest.mark.anyio
async def test_push_to_accepts_sync_line_sdk_response():
    class SyncLineApi:
        def __init__(self):
            self.request = None

        def push_message(self, request):
            self.request = request
            return object()

    api = SyncLineApi()
    with patch("app.line.webhook._messaging_api", api), \
         patch("app.line.webhook.logger.exception") as mock_log_exception:
        await _push_to("U1", "hello")

    assert api.request.to == "U1"
    assert api.request.messages[0].text == "hello"
    mock_log_exception.assert_not_called()

@pytest.mark.anyio
async def test_handle_webhook_returns_204_on_client_disconnect():
    async def disconnected_body():
        raise ClientDisconnect()

    request = SimpleNamespace(body=disconnected_body, headers={})

    response = await handle_webhook(request)

    assert response.status_code == 204
