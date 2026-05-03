from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
from decimal import Decimal

import pytest
from gspread.exceptions import APIError

from app.line.parser import (
    ParsedPostback,
    POSTBACK_CANCEL_IMPORT_REPORT,
    POSTBACK_CANCEL_COLLECTION,
    POSTBACK_CONFIRM_IMPORT_REPORT,
    POSTBACK_CONFIRM_READING,
    POSTBACK_HELP,
    POSTBACK_HELP_FLOW,
    POSTBACK_HISTORY,
    POSTBACK_HISTORY_CURRENT,
    POSTBACK_HISTORY_SELECT_WEEK,
    POSTBACK_SELECT_METER,
    POSTBACK_SKIP_METER,
    POSTBACK_START_COLLECTION,
    POSTBACK_SETTINGS,
    POSTBACK_SETTINGS_CONFIRM_CHANGE,
    POSTBACK_SETTINGS_EDIT_RATE,
    POSTBACK_SETTINGS_IMPORT_REPORT,
)
from app.line.webhook import _handle_postback, _next_meter_to_capture
from app.services.batch_service import BatchProgress
from app.services.confirmation_service import PendingConfirmation
from app.services.session_service import (
    COLLECTION_WAITING_IMAGE,
    REPORT_IMPORT_IDLE,
    REPORT_IMPORT_WAITING_IMAGE,
    get_batch_id,
    get_collection_current_meter,
    get_collection_state,
    get_pending_report_import,
    get_report_import_state,
    set_collection_meter_skipped,
    set_batch_id,
    set_collection_current_meter,
    set_pending_report_import,
    set_pending_setting_change,
    set_pending_confirmation,
    set_report_import_state,
    PendingReportImport,
)


class _FakeSheetsResponse:
    text = "Quota exceeded"

    def json(self):
        return {
            "error": {
                "code": 429,
                "message": "Quota exceeded",
                "status": "RESOURCE_EXHAUSTED",
            }
        }


@pytest.fixture(autouse=True)
def _clean_sessions():
    from app.services import session_service

    session_service._store = session_service.InMemorySessionStore()
    with patch("app.services.confirmation_service.get_latest_pending_confirmation", return_value=None):
        yield
    session_service._store = session_service.InMemorySessionStore()


def _pending_import(batch_id: str = "2026-W18-U1") -> PendingReportImport:
    return PendingReportImport(
        batch_id=batch_id,
        week="2026-W18",
        date="2026-04-27",
        rows=[
            {
                "meter_id": f"M{i}",
                "current_value": str(1000 + i),
                "last_value": str(900 + i),
                "produced_unit": "100",
                "rate": "4.2",
                "amount": "420",
            }
            for i in range(1, 9)
        ],
        total_produced_unit=Decimal("800"),
        total_amount=Decimal("3360"),
        ocr_raw_text="old report",
        image_message_id="img-1",
    )


@pytest.mark.anyio
async def test_start_collection_postback_starts_linear_flow():
    with patch("app.line.webhook.ensure_batch_id", return_value="2026-W19-U1"), \
         patch("app.line.webhook.get_batch_progress", return_value=None), \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_START_COLLECTION), "rt")

    assert mock_reply.await_count == 1
    assert len(mock_reply.await_args.args[1]) == 2
    assert get_collection_state("U1") == COLLECTION_WAITING_IMAGE
    assert get_collection_current_meter("U1") == "M1"


@pytest.mark.anyio
async def test_skip_meter_moves_to_next_machine():
    set_batch_id("U1", "2026-W19-U1")
    set_collection_current_meter("U1", "M1")
    progress = BatchProgress(
        batch_id="2026-W19-U1",
        week="2026-W19",
        status="collecting",
        expected_meter_count=8,
        confirmed_meter_count=0,
        missing_meter_ids=["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"],
    )

    with patch("app.line.webhook.get_batch_progress", return_value=progress), \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock):
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_SKIP_METER, meter_id="M1"), "rt")

    assert get_collection_current_meter("U1") == "M2"


@pytest.mark.anyio
async def test_select_meter_postback_updates_current_meter():
    with patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_SELECT_METER, meter_id="M3"), "rt")

    assert get_collection_current_meter("U1") == "M3"
    assert get_collection_state("U1") == COLLECTION_WAITING_IMAGE
    assert mock_reply.await_count == 1


@pytest.mark.anyio
async def test_confirm_postback_moves_state_without_errors():
    with patch("app.line.webhook.confirm_pending", return_value=(
        PendingConfirmation(meter_id="M1"),
        "บันทึก M1 เรียบร้อย",
        "2026-W19-U1",
    )), \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply, \
         patch("app.line.webhook._push_to", new_callable=AsyncMock) as mock_push, \
         patch(
             "app.line.webhook.get_batch_progress",
             return_value=BatchProgress(
                batch_id="2026-W19-U1",
                week="2026-W19",
                status="collecting",
                expected_meter_count=8,
                confirmed_meter_count=1,
                missing_meter_ids=["M2","M3","M4","M5","M6","M7","M8"],
              ),
         ):
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_CONFIRM_READING, meter_id="M1"), "rt")

    mock_reply.assert_awaited_once_with("rt", "กำลังบันทึก M1 ครับ...")
    assert mock_push.await_count == 1
    pushed_messages = mock_push.await_args.args[1]
    assert len(pushed_messages) == 2
    assert pushed_messages[0] == "บันทึก M1 เรียบร้อย"


@pytest.mark.anyio
async def test_confirm_postback_uses_pending_meter_in_loading_message():
    set_pending_confirmation(source_id="U1", meter_id="M2", batch_id="2026-W19-U1")

    with patch("app.line.webhook.confirm_pending", return_value=(None, "ไม่มีค่าที่รอยืนยันครับ", None)), \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply, \
         patch("app.line.webhook._push_to", new_callable=AsyncMock):
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_CONFIRM_READING), "rt")

    mock_reply.assert_awaited_once_with("rt", "กำลังบันทึก M2 ครับ...")


@pytest.mark.anyio
async def test_cancel_collection_marks_pending_cancelled():
    set_batch_id("U1", "2026-W19-U1")
    set_pending_confirmation(
        source_id="U1",
        meter_id="M2",
        confirmation_id="cnf_1",
        batch_id="2026-W19-U1",
    )

    with patch("app.services.confirmation_service.update_pending_confirmation_status") as mock_update, \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock):
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_CANCEL_COLLECTION), "rt")

    mock_update.assert_called_once_with("cnf_1", "cancelled")
    assert get_batch_id("U1") is None


@pytest.mark.anyio
async def test_help_and_history_postback_are_supported():
    with patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_HELP), "rt")
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_HISTORY), "rt")

    assert mock_reply.await_count == 2
    assert "ต้องการดูวิธีใช้งานส่วนไหน" in mock_reply.await_args_list[0].args[1].text


@pytest.mark.anyio
async def test_help_flow_postback_replies_with_selected_topic():
    with patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        await _handle_postback(
            "U1",
            ParsedPostback(type=POSTBACK_HELP_FLOW, topic="latest_report"),
            "rt",
        )

    payload = mock_reply.await_args.args[1]
    assert "วิธีดูรายงานล่าสุด" in payload.text

@pytest.mark.anyio
async def test_history_current_postback_shows_summary_actions():
    summary = SimpleNamespace(
        batch_id="2026-W19-U1",
        week="2026-W19",
        status="collecting",
        expected_meter_count=8,
        confirmed_meter_count=1,
        missing_meter_ids=["M2", "M3"],
        produced_unit=100,
        amount=420,
        readings=[{"meter_id": "M1", "current_value": "100", "produced_unit": "100"}],
    )

    with patch("app.line.webhook.history_service.get_current_batch_summary", return_value=summary), \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_HISTORY_CURRENT), "rt")

    payload = mock_reply.await_args.args[1]
    assert "ประวัติรอบปัจจุบัน" in payload.text
    assert "history_batch_detail" in str(payload)

@pytest.mark.anyio
async def test_history_select_week_postback_shows_recent_batches():
    summaries = [
        SimpleNamespace(
            batch_id="2026-W18-U1",
            week="2026-W18",
            expected_meter_count=8,
            confirmed_meter_count=8,
        )
    ]

    with patch("app.line.webhook.history_service.get_recent_batch_summaries", return_value=summaries), \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_HISTORY_SELECT_WEEK), "rt")

    payload = mock_reply.await_args.args[1]
    assert "ประวัติย้อนหลัง 1 เดือน" in payload.text
    assert "2026-W18" in payload.text
    assert "history_batch" in str(payload)

@pytest.mark.anyio
async def test_settings_postback_branches_by_operator_role():
    with patch("app.line.webhook.settings_service.is_admin", return_value=False), \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_SETTINGS), "rt")

    payload = mock_reply.await_args.args[1]
    assert "การแก้ไขต้องใช้สิทธิ์ผู้ดูแลระบบ" in payload.text
    assert "settings_edit_rate" not in str(payload)
    assert "settings_import_report" not in str(payload)

    with patch("app.line.webhook.settings_service.is_admin", return_value=True), \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_SETTINGS), "rt")

    assert "settings_import_report" in str(mock_reply.await_args.args[1])


@pytest.mark.anyio
async def test_admin_can_start_report_import_from_settings():
    with patch("app.line.webhook.settings_service.is_admin", return_value=True), \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_SETTINGS_IMPORT_REPORT), "rt")

    assert get_report_import_state("U1") == REPORT_IMPORT_WAITING_IMAGE
    assert "นำข้อมูลเข้าด้วยรายงานเก่า" in mock_reply.await_args.args[1].text


@pytest.mark.anyio
async def test_non_admin_cannot_start_report_import():
    with patch("app.line.webhook.settings_service.is_admin", return_value=False), \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_SETTINGS_IMPORT_REPORT), "rt")

    assert get_report_import_state("U1") == REPORT_IMPORT_IDLE
    assert "การแก้ไขต้องใช้สิทธิ์ผู้ดูแลระบบ" in mock_reply.await_args.args[1].text

@pytest.mark.anyio
async def test_admin_edit_rate_creates_input_step():
    with patch("app.line.webhook.settings_service.is_admin", return_value=True), \
         patch("app.line.webhook.settings_service.get_current_settings", return_value={"default_rate": "4.2"}), \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_SETTINGS_EDIT_RATE), "rt")

    payload = mock_reply.await_args.args[1]
    assert "อัตราค่าไฟปัจจุบัน" in payload.text
    assert "4.2" in payload.text

@pytest.mark.anyio
async def test_settings_confirm_change_applies_pending_change():
    set_pending_setting_change(
        source_id="U1",
        change_id="chg_1",
        key="default_rate",
        old_value="4.2",
        new_value="4.5",
        label="อัตราค่าไฟ",
        impact="ใช้ครั้งถัดไป",
    )

    with patch("app.line.webhook.settings_service.is_admin", return_value=True), \
         patch("app.line.webhook.settings_service.apply_setting_change") as mock_apply, \
         patch("app.line.webhook.settings_service.get_current_settings", return_value={"default_rate": "4.5"}), \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        await _handle_postback(
            "U1",
            ParsedPostback(type=POSTBACK_SETTINGS_CONFIRM_CHANGE, change_id="chg_1"),
            "rt",
        )

    mock_apply.assert_called_once_with("U1", "default_rate", "4.2", "4.5")
    assert "การตั้งค่าปัจจุบัน" in mock_reply.await_args.args[1].text


@pytest.mark.anyio
async def test_confirm_report_import_appends_batch_and_readings():
    set_pending_report_import("U1", _pending_import())

    with patch("app.line.webhook.settings_service.is_admin", return_value=True), \
         patch("app.services.report_import_service.repositories.get_readings_by_batch", return_value=[]), \
         patch("app.services.report_import_service.repositories.get_batch_by_id", return_value=None), \
         patch("app.services.report_import_service.repositories.append_batch") as mock_append_batch, \
         patch("app.services.report_import_service.repositories.append_reading") as mock_append_reading, \
         patch("app.services.report_import_service.repositories.update_batch_confirmed_count") as mock_update_count, \
         patch("app.services.report_import_service.repositories.update_batch_status") as mock_update_status, \
         patch("app.services.report_import_service.generate_report_image", return_value="reports/2026-W18-U1.png") as mock_generate, \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_CONFIRM_IMPORT_REPORT), "rt")

    mock_append_batch.assert_called_once()
    assert mock_append_reading.call_count == 8
    first_reading = mock_append_reading.call_args_list[0].args[0]
    assert first_reading["batch_id"] == "2026-W18-U1"
    assert first_reading["line_source_id"] == "U1"
    assert first_reading["confirmation_method"] == "manual_report_import"
    mock_update_count.assert_called_once_with("2026-W18-U1", 8)
    mock_update_status.assert_called_once_with("2026-W18-U1", "complete")
    mock_generate.assert_called_once_with("2026-W18-U1")
    assert get_batch_id("U1") == "2026-W18-U1"
    assert "นำเข้ารายงานเก่าเรียบร้อย" in mock_reply.await_args.args[1].text


@pytest.mark.anyio
async def test_confirm_report_import_duplicate_batch_does_not_append():
    set_pending_report_import("U1", _pending_import())

    with patch("app.line.webhook.settings_service.is_admin", return_value=True), \
         patch("app.services.report_import_service.repositories.get_readings_by_batch", return_value=[{"meter_id": "M1"}]), \
         patch("app.services.report_import_service.repositories.get_batch_by_id", return_value={"status": "collecting"}), \
         patch("app.services.report_import_service.repositories.append_batch") as mock_append_batch, \
         patch("app.services.report_import_service.repositories.append_reading") as mock_append_reading, \
         patch("app.services.report_import_service.generate_report_image") as mock_generate, \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_CONFIRM_IMPORT_REPORT), "rt")

    mock_append_batch.assert_not_called()
    mock_append_reading.assert_not_called()
    mock_generate.assert_not_called()
    assert "มีข้อมูลอยู่แล้ว" in mock_reply.await_args.args[1].text


@pytest.mark.anyio
async def test_cancel_report_import_clears_state():
    set_pending_report_import("U1", _pending_import())

    with patch("app.line.webhook.settings_service.is_admin", return_value=True), \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock):
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_CANCEL_IMPORT_REPORT), "rt")

    assert get_report_import_state("U1") == REPORT_IMPORT_IDLE


@pytest.mark.anyio
async def test_non_admin_cannot_cancel_report_import():
    set_pending_report_import("U1", _pending_import())
    set_report_import_state("U1", REPORT_IMPORT_WAITING_IMAGE)

    with patch("app.line.webhook.settings_service.is_admin", return_value=False), \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_CANCEL_IMPORT_REPORT), "rt")

    assert get_report_import_state("U1") == REPORT_IMPORT_WAITING_IMAGE
    assert "การแก้ไขต้องใช้สิทธิ์ผู้ดูแลระบบ" in mock_reply.await_args.args[1].text
    assert get_pending_report_import("U1") is not None


def test_next_meter_linear_with_skipped_meters():
    set_batch_id("U1", "2026-W19-U1")
    progress = BatchProgress(
        batch_id="2026-W19-U1",
        week="2026-W19",
        status="collecting",
        expected_meter_count=8,
        confirmed_meter_count=0,
        missing_meter_ids=["M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8"],
    )
    with patch("app.line.webhook.get_batch_progress", return_value=progress):
        assert _next_meter_to_capture("U1", "2026-W19-U1") == "M1"
        set_collection_meter_skipped("U1", "M1")
        assert _next_meter_to_capture("U1", "2026-W19-U1") == "M2"


@pytest.mark.anyio
async def test_postback_safety_replies_on_sheets_api_error():
    from app.line.webhook import _handle_postback_safely

    with patch("app.line.webhook._handle_postback", side_effect=APIError(_FakeSheetsResponse())), \
         patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        await _handle_postback_safely("U1", ParsedPostback(type=POSTBACK_START_COLLECTION), "rt")

    assert mock_reply.await_count == 1
    assert "Google Sheets" in mock_reply.await_args.args[1]
