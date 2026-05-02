from unittest.mock import Mock, patch

import pytest

from app.line.parser import ParsedCommand, GEN, HELP, REPORT
from app.line.webhook import _build_reply, _resolve_batch_id
from app.services.session_service import set_batch_id


@pytest.fixture(autouse=True)
def _clean_sessions():
    from app.services import session_service
    session_service._store = session_service.InMemorySessionStore()
    yield
    session_service._store = session_service.InMemorySessionStore()


def test_gen_without_batch_returns_no_data_message():
    reply = _build_reply(ParsedCommand(type=GEN), "U1")

    assert "ยังไม่มีข้อมูลรอบนี้" in reply


def test_gen_generates_report_for_current_batch():
    set_batch_id("U1", "2026-W19-U1")

    with patch("app.line.webhook.generate_report_image") as mock_generate, \
         patch("app.line.webhook._build_report_url") as mock_build_url:
        mock_generate.return_value = "reports/2026-W19-U1.png"
        mock_build_url.return_value = "http://localhost:8000/reports/2026-W19-U1.png"
        reply = _build_reply(ParsedCommand(type=GEN), "U1")

    mock_generate.assert_called_once_with("2026-W19-U1")
    mock_build_url.assert_called_once_with("2026-W19-U1.png")
    assert "สร้างรูปเรียบร้อย" in reply
    assert "http://localhost:8000/reports/2026-W19-U1.png" in reply


def test_gen_with_no_report_data_returns_message():
    set_batch_id("U1", "2026-W19-U1")

    with patch("app.line.webhook.generate_report_image", return_value=None):
        reply = _build_reply(ParsedCommand(type=GEN), "U1")

    assert "ยังไม่มีข้อมูลสำหรับสร้างรูป" in reply


def test_gen_with_week_ref_generates_report_for_source_week():
    with patch("app.line.webhook.generate_report_image") as mock_generate, \
         patch("app.line.webhook._build_report_url") as mock_build_url:
        mock_generate.return_value = "reports/2026-W18-U1.png"
        mock_build_url.return_value = "http://localhost:8000/reports/2026-W18-U1.png"
        reply = _build_reply(ParsedCommand(type=GEN, batch_id="2026-w18"), "U1")

    mock_generate.assert_called_once_with("2026-W18-U1")
    mock_build_url.assert_called_once_with("2026-W18-U1.png")
    assert "http://localhost:8000/reports/2026-W18-U1.png" in reply


def test_gen_with_batch_id_generates_report_for_that_batch():
    with patch("app.line.webhook.generate_report_image") as mock_generate, \
         patch("app.line.webhook._build_report_url") as mock_build_url:
        mock_generate.return_value = "reports/2026-W18-UabcDef.png"
        mock_build_url.return_value = "http://localhost:8000/reports/2026-W18-UabcDef.png"
        reply = _build_reply(ParsedCommand(type=GEN, batch_id="2026-W18-UabcDef"), "U1")

    mock_generate.assert_called_once_with("2026-W18-UabcDef")
    mock_build_url.assert_called_once_with("2026-W18-UabcDef.png")
    assert "http://localhost:8000/reports/2026-W18-UabcDef.png" in reply


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


def test_help_includes_gen_command():
    reply = _build_reply(ParsedCommand(type=HELP), "U1")

    assert "GEN" in reply
    assert "สร้างรูปรายงาน" in reply
    assert "GEN <batch_id|YYYY-Www>" in reply
    assert "REPORT" in reply
    assert "ส่งรูปรายงานเป็นรูป" in reply
    assert "REPORT <batch_id>" in reply
