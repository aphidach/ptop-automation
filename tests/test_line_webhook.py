from unittest.mock import patch

import pytest

from app.line.parser import ParsedCommand, GEN, HELP
from app.line.webhook import _build_reply
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

    with patch("app.line.webhook.generate_report_image") as mock_generate:
        mock_generate.return_value = "reports/2026-W19-U1.png"
        reply = _build_reply(ParsedCommand(type=GEN), "U1")

    mock_generate.assert_called_once_with("2026-W19-U1")
    assert "สร้างรูปเรียบร้อย" in reply
    assert "reports/2026-W19-U1.png" in reply


def test_gen_with_no_report_data_returns_message():
    set_batch_id("U1", "2026-W19-U1")

    with patch("app.line.webhook.generate_report_image", return_value=None):
        reply = _build_reply(ParsedCommand(type=GEN), "U1")

    assert "ยังไม่มีข้อมูลสำหรับสร้างรูป" in reply


def test_help_includes_gen_command():
    reply = _build_reply(ParsedCommand(type=HELP), "U1")

    assert "GEN" in reply
    assert "สร้างรูปรายงาน" in reply
