from unittest.mock import AsyncMock, Mock, patch
from types import SimpleNamespace

import pytest
from linebot.v3.messaging import FlexMessage

from decimal import Decimal
from starlette.requests import ClientDisconnect

from app.config import settings
from app.line.parser import METER_VALUE, ParsedCommand, GEN, HELP, REPORT, STATUS, CANCEL, METER, OK, UNKNOWN
from app.line.webhook import (
    _build_reply,
    _build_status_message,
    _coerce_manual_value_command,
    handle_webhook,
    _push_to,
    _read_ocr_image,
    _reply_to,
    _resolve_batch_id,
    _restore_collection_from_current_batch,
)
from app.services.batch_service import BatchProgress
from app.services.session_service import (
    COLLECTION_WAITING_IMAGE,
    COLLECTION_WAITING_MANUAL_VALUE,
    REPORT_IMPORT_WAITING_IMAGE,
    get_batch_id,
    get_collection_current_meter,
    get_collection_state,
    set_batch_id,
    set_collection_current_meter,
    set_collection_state,
    set_latest_meter,
    set_pending_confirmation,
    set_report_import_state,
)


@pytest.fixture(autouse=True)
def _clean_sessions():
    from app.services import session_service
    session_service._store = session_service.InMemorySessionStore()
    with patch("app.services.confirmation_service.get_latest_pending_confirmation", return_value=None):
        yield
    session_service._store = session_service.InMemorySessionStore()


class _FakeLineRequest:
    headers = {"X-Line-Signature": "test-signature"}

    def __init__(self, body: bytes = b"{}"):
        self._body = body

    async def body(self):
        return self._body


def _line_text_event(source, text: str = "HELP"):
    return SimpleNamespace(
        type="message",
        source=source,
        message=SimpleNamespace(type="text", id="msg-1", text=text),
        reply_token="reply-token",
        delivery_context=None,
        webhook_event_id="event-1",
    )


def _line_image_event(source):
    return SimpleNamespace(
        type="message",
        source=source,
        message=SimpleNamespace(type="image", id="img-1"),
        reply_token="reply-token",
        delivery_context=None,
        webhook_event_id="event-1",
    )


def test_gen_without_batch_returns_no_data_message():
    reply = _build_reply(ParsedCommand(type=GEN), "U1")

    assert "ยังไม่มีข้อมูลรอบนี้" in reply


def test_gen_schedules_image_send_for_current_batch():
    set_batch_id("U1", "2026-W19-U1")

    with patch("app.line.webhook.send_report", new=Mock(return_value="send-report-task")) as mock_send_report, \
         patch("app.line.webhook.asyncio.create_task") as mock_create_task, \
         patch(
             "app.line.message_builders.reports.build_report_data",
             return_value=SimpleNamespace(
                 week="2026-W19",
                 readings=[1, 2, 3],
                 total_produced_unit=Decimal("1234.5"),
                 total_amount=Decimal("4567.89"),
             ),
         ):
        reply = _build_reply(ParsedCommand(type=GEN), "U1")

    mock_send_report.assert_called_once_with("2026-W19-U1", "U1")
    mock_create_task.assert_called_once_with("send-report-task")
    assert isinstance(reply, FlexMessage)
    payload = reply.dict(by_alias=True, exclude_none=True)
    assert payload["altText"] == "รายงานสัปดาห์ 2026-W19"
    assert "action=history_batch_detail&batch_id=2026-W19-U1" in str(payload)
    assert "action=latest_report&batch_id=2026-W19-U1" in str(payload)


def test_gen_does_not_schedule_image_send_when_report_is_unavailable():
    set_batch_id("U1", "2026-W19-U1")

    with patch("app.line.webhook.send_report") as mock_send_report, \
         patch("app.line.webhook.asyncio.create_task") as mock_create_task, \
         patch("app.line.message_builders.reports.build_report_data", return_value=None):
        reply = _build_reply(ParsedCommand(type=GEN), "U1")

    mock_send_report.assert_not_called()
    mock_create_task.assert_not_called()
    assert isinstance(reply, FlexMessage)
    payload = reply.dict(by_alias=True, exclude_none=True)
    assert payload["altText"] == "รายงานยังไม่พร้อม"
    assert "2026-W19" in str(payload)


def test_gen_with_week_ref_schedules_image_send_for_source_week():
    with patch("app.line.webhook.send_report", new=Mock(return_value="send-report-task")) as mock_send_report, \
         patch("app.line.webhook.asyncio.create_task") as mock_create_task, \
         patch(
             "app.line.message_builders.reports.build_report_data",
             return_value=SimpleNamespace(
                 week="2026-W18",
                 readings=[1, 2],
                 total_produced_unit=Decimal("987.6"),
                 total_amount=Decimal("321"),
             ),
         ):
        reply = _build_reply(ParsedCommand(type=GEN, batch_id="2026-w18"), "U1")

    mock_send_report.assert_called_once_with("2026-W18-U1", "U1")
    mock_create_task.assert_called_once_with("send-report-task")
    assert isinstance(reply, FlexMessage)
    payload = reply.dict(by_alias=True, exclude_none=True)
    assert payload["altText"] == "รายงานสัปดาห์ 2026-W18"


def test_gen_with_batch_id_schedules_image_send_for_that_batch():
    with patch("app.line.webhook.send_report", new=Mock(return_value="send-report-task")) as mock_send_report, \
         patch("app.line.webhook.asyncio.create_task") as mock_create_task, \
         patch(
             "app.line.message_builders.reports.build_report_data",
             return_value=SimpleNamespace(
                 week="2026-W18",
                 readings=[1],
                 total_produced_unit=Decimal("50.0"),
                 total_amount=Decimal("200.0"),
             ),
         ):
        reply = _build_reply(ParsedCommand(type=GEN, batch_id="2026-W18-UabcDef"), "U1")

    mock_send_report.assert_called_once_with("2026-W18-UabcDef", "U1")
    mock_create_task.assert_called_once_with("send-report-task")
    assert isinstance(reply, FlexMessage)
    payload = reply.dict(by_alias=True, exclude_none=True)
    assert payload["altText"] == "รายงานสัปดาห์ 2026-W18"


def test_resolve_batch_id_uses_current_session_when_empty():
    set_batch_id("U1", "2026-W19-U1")

    assert _resolve_batch_id(None, "U1") == "2026-W19-U1"


def test_resolve_batch_id_converts_week_ref_to_source_batch_id():
    assert _resolve_batch_id("2026-w18", "U1") == "2026-W18-U1"


def test_resolve_batch_id_preserves_full_batch_id_case():
    assert _resolve_batch_id("2026-W18-UabcDef", "U1") == "2026-W18-UabcDef"


def test_restore_collection_from_current_batch_uses_sheet_progress():
    progress = BatchProgress(
        batch_id="2026-W19-U1",
        week="2026-W19",
        status="collecting",
        expected_meter_count=8,
        confirmed_meter_count=1,
        missing_meter_ids=["M2", "M3", "M4", "M5", "M6", "M7", "M8"],
    )

    with patch("app.line.webhook.generate_batch_id", return_value="2026-W19-U1"), \
         patch("app.line.webhook.get_batch_progress", return_value=progress):
        meter_id = _restore_collection_from_current_batch("U1")

    assert meter_id == "M2"
    assert get_batch_id("U1") == "2026-W19-U1"
    assert get_collection_current_meter("U1") == "M2"
    assert get_collection_state("U1") == COLLECTION_WAITING_IMAGE


def test_report_without_batch_returns_no_data_message():
    reply = _build_reply(ParsedCommand(type=REPORT), "U1")

    assert "ยังไม่มีข้อมูลรอบนี้" in reply


def test_report_schedules_image_send_for_current_batch():
    set_batch_id("U1", "2026-W19-U1")

    with patch("app.line.webhook.send_report", new=Mock(return_value="send-report-task")) as mock_send_report, \
         patch("app.line.webhook.asyncio.create_task") as mock_create_task, \
         patch(
             "app.line.message_builders.reports.build_report_data",
             return_value=SimpleNamespace(
                 week="2026-W19",
                 readings=[1, 2, 3, 4],
                 total_produced_unit=Decimal("1234.5"),
                 total_amount=Decimal("4567.89"),
             ),
         ):
        reply = _build_reply(ParsedCommand(type=REPORT), "U1")

    mock_send_report.assert_called_once_with("2026-W19-U1", "U1")
    mock_create_task.assert_called_once_with("send-report-task")
    assert isinstance(reply, FlexMessage)
    payload = reply.dict(by_alias=True, exclude_none=True)
    assert payload["altText"] == "รายงานสัปดาห์ 2026-W19"


def test_report_with_batch_id_schedules_image_send_for_that_batch():
    with patch("app.line.webhook.send_report", new=Mock(return_value="send-report-task")) as mock_send_report, \
         patch("app.line.webhook.asyncio.create_task") as mock_create_task, \
         patch(
             "app.line.message_builders.reports.build_report_data",
             return_value=SimpleNamespace(
                 week="2026-W18",
                 readings=[1],
                 total_produced_unit=Decimal("50.0"),
                 total_amount=Decimal("200.0"),
             ),
         ):
        reply = _build_reply(
            ParsedCommand(type=REPORT, batch_id="2026-W18-U08585bd3f4116f311ae320cab4e9e1b6"),
            "U1",
        )

    mock_send_report.assert_called_once_with(
        "2026-W18-U08585bd3f4116f311ae320cab4e9e1b6",
        "U1",
    )
    mock_create_task.assert_called_once_with("send-report-task")
    assert isinstance(reply, FlexMessage)
    payload = reply.dict(by_alias=True, exclude_none=True)
    assert payload["altText"] == "รายงานสัปดาห์ 2026-W18"


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

    assert isinstance(reply, FlexMessage)
    payload = reply.dict(by_alias=True, exclude_none=True)
    assert payload["altText"] == "สถานะรอบบันทึก"
    assert "เครื่องปัจจุบัน" in str(payload)
    assert "M2" in str(payload)


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
async def test_production_ocr_reader_uses_google_client(monkeypatch):
    import app.line.webhook as webhook
    from app.ocr.google_vision import GoogleVisionOcrClient

    class FakeGoogleVisionClient:
        def __init__(self):
            self.image_path = None

        def read_image(self, image_path):
            self.image_path = image_path
            return "ocr-result"

    assert isinstance(webhook._ocr_client, GoogleVisionOcrClient)
    fake_client = FakeGoogleVisionClient()
    monkeypatch.setattr(webhook, "_ocr_client", fake_client)

    result = await _read_ocr_image("meter.jpg")

    assert result == "ocr-result"
    assert fake_client.image_path == "meter.jpg"


@pytest.mark.anyio
async def test_handle_webhook_ignores_unauthorized_line_user(monkeypatch):
    monkeypatch.setattr(settings, "ALLOWED_LINE_SOURCE_IDS", ["G1"])
    monkeypatch.setattr(settings, "ALLOWED_LINE_USER_IDS", ["U1"])
    monkeypatch.setattr(settings, "ADMIN_LINE_USER_IDS", [])
    monkeypatch.setattr(settings, "OWNER_LINE_USER_IDS", [])
    event = _line_text_event(SimpleNamespace(type="group", group_id="G1", user_id="U2"), "STATUS")

    with patch("app.line.webhook._webhook_parser.parse", return_value=[event]), \
         patch("app.line.webhook._build_text_reply") as mock_build_reply, \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        response = await handle_webhook(_FakeLineRequest())

    assert response == {"ok": True}
    mock_build_reply.assert_not_called()
    mock_reply.assert_not_awaited()


@pytest.mark.anyio
async def test_handle_webhook_allows_group_chat_and_uses_chat_source_id(monkeypatch):
    monkeypatch.setattr(settings, "ALLOWED_LINE_SOURCE_IDS", ["G1"])
    monkeypatch.setattr(settings, "ALLOWED_LINE_USER_IDS", ["U1"])
    monkeypatch.setattr(settings, "ADMIN_LINE_USER_IDS", [])
    monkeypatch.setattr(settings, "OWNER_LINE_USER_IDS", [])
    event = _line_text_event(SimpleNamespace(type="group", group_id="G1", user_id="U1"), "STATUS")

    with patch("app.line.webhook._webhook_parser.parse", return_value=[event]), \
         patch("app.line.webhook._build_text_reply", return_value="ok") as mock_build_reply, \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        response = await handle_webhook(_FakeLineRequest())

    assert response == {"ok": True}
    assert mock_build_reply.call_args.args[1] == "G1"
    mock_reply.assert_awaited_once_with("reply-token", "ok")


@pytest.mark.anyio
async def test_handle_webhook_logs_line_source_and_user_id(monkeypatch):
    monkeypatch.setattr(settings, "ALLOWED_LINE_SOURCE_IDS", ["G1"])
    monkeypatch.setattr(settings, "ALLOWED_LINE_USER_IDS", ["U1"])
    monkeypatch.setattr(settings, "ADMIN_LINE_USER_IDS", [])
    monkeypatch.setattr(settings, "OWNER_LINE_USER_IDS", [])
    event = _line_text_event(SimpleNamespace(type="group", group_id="G1", user_id="U1"), "STATUS")

    with patch("app.line.webhook._webhook_parser.parse", return_value=[event]), \
         patch("app.line.webhook._build_text_reply", return_value="ok"), \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock), \
         patch("app.line.webhook.logger.info") as mock_log_info:
        response = await handle_webhook(_FakeLineRequest())

    assert response == {"ok": True}
    assert any(
        call.args
        and call.args[0].startswith("LINE event: type=message")
        and "line_source_id=%s" in call.args[0]
        and "line_user_id=%s" in call.args[0]
        and call.args[-2] == "G1"
        and call.args[-1] == "U1"
        for call in mock_log_info.call_args_list
    )


@pytest.mark.anyio
async def test_handle_webhook_image_in_import_mode_skips_meter_ocr(monkeypatch):
    monkeypatch.setattr(settings, "ALLOWED_LINE_SOURCE_IDS", ["G1"])
    monkeypatch.setattr(settings, "ALLOWED_LINE_USER_IDS", ["U1"])
    monkeypatch.setattr(settings, "ADMIN_LINE_USER_IDS", ["U1"])
    monkeypatch.setattr(settings, "OWNER_LINE_USER_IDS", [])
    set_report_import_state("G1", REPORT_IMPORT_WAITING_IMAGE)
    set_collection_current_meter("G1", "M1")
    event = _line_image_event(SimpleNamespace(type="group", group_id="G1", user_id="U1"))

    with patch("app.line.webhook._webhook_parser.parse", return_value=[event]), \
         patch("app.line.webhook.download_image", new_callable=AsyncMock, return_value="report.jpg"), \
         patch("app.line.webhook._process_report_import_image", new=Mock(return_value="report-task")) as mock_import, \
         patch("app.line.webhook._process_ocr_and_confirm", new=Mock(return_value="meter-task")) as mock_meter, \
         patch("app.line.webhook.asyncio.create_task") as mock_create_task, \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        response = await handle_webhook(_FakeLineRequest())

    assert response == {"ok": True}
    mock_import.assert_called_once_with("G1", "report.jpg", "img-1")
    mock_meter.assert_not_called()
    mock_create_task.assert_called_once_with("report-task")
    assert "รับรูปรายงานเก่า" in mock_reply.await_args.args[1]


@pytest.mark.anyio
async def test_handle_webhook_returns_204_on_client_disconnect():
    async def disconnected_body():
        raise ClientDisconnect()

    request = SimpleNamespace(body=disconnected_body, headers={})

    response = await handle_webhook(request)

    assert response.status_code == 204
