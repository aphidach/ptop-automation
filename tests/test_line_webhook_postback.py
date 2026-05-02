from unittest.mock import AsyncMock, patch

import pytest
from gspread.exceptions import APIError

from app.line.parser import (
    ParsedPostback,
    POSTBACK_CONFIRM_READING,
    POSTBACK_HELP,
    POSTBACK_HISTORY,
    POSTBACK_SELECT_METER,
    POSTBACK_SKIP_METER,
    POSTBACK_START_COLLECTION,
)
from app.line.webhook import _handle_postback, _next_meter_to_capture
from app.services.batch_service import BatchProgress
from app.services.confirmation_service import PendingConfirmation
from app.services.session_service import (
    COLLECTION_WAITING_IMAGE,
    get_collection_current_meter,
    get_collection_state,
    set_collection_meter_skipped,
    set_batch_id,
    set_collection_current_meter,
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
    yield
    session_service._store = session_service.InMemorySessionStore()


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
    assert mock_reply.await_count >= 1


@pytest.mark.anyio
async def test_help_and_history_postback_are_supported():
    with patch("app.line.webhook._reply_to", new_callable=AsyncMock) as mock_reply:
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_HELP), "rt")
        await _handle_postback("U1", ParsedPostback(type=POSTBACK_HISTORY), "rt")

    assert mock_reply.await_count == 2


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
