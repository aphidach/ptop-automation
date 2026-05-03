from decimal import Decimal
from unittest.mock import patch

from app.services.report_import_service import CONFIRMATION_METHOD, confirm_report_import
from app.services.session_service import PendingReportImport


def _pending_import() -> PendingReportImport:
    return PendingReportImport(
        batch_id="2026-W18-U1",
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


def _existing_row(row: dict[str, str], line_source_id: str = "U1") -> dict[str, str]:
    return {
        **row,
        "batch_id": "2026-W18-U1",
        "week": "2026-W18",
        "date": "2026-04-27",
        "line_source_id": line_source_id,
        "confirmation_method": CONFIRMATION_METHOD,
    }


def test_confirm_report_import_partial_retry_appends_missing_rows():
    pending = _pending_import()
    existing = [_existing_row(row) for row in pending.rows[:3]]

    with patch("app.services.report_import_service.repositories.get_readings_by_batch", return_value=existing), \
         patch("app.services.report_import_service.repositories.get_batch_by_id", return_value={"status": "collecting"}), \
         patch("app.services.report_import_service.repositories.append_batch") as mock_append_batch, \
         patch("app.services.report_import_service.repositories.append_reading") as mock_append_reading, \
         patch("app.services.report_import_service.repositories.update_batch_confirmed_count") as mock_update_count, \
         patch("app.services.report_import_service.repositories.update_batch_status") as mock_update_status, \
         patch("app.services.report_import_service.generate_report_image", return_value="reports/2026-W18-U1.png"):
        result = confirm_report_import("U1", pending, line_user_id="Uadmin")

    assert result.success is True
    mock_append_batch.assert_not_called()
    assert mock_append_reading.call_count == 5
    appended_meter_ids = [call.args[0]["meter_id"] for call in mock_append_reading.call_args_list]
    assert appended_meter_ids == ["M4", "M5", "M6", "M7", "M8"]
    mock_update_count.assert_called_once_with("2026-W18-U1", 8)
    mock_update_status.assert_called_once_with("2026-W18-U1", "complete")


def test_confirm_report_import_conflict_does_not_append():
    pending = _pending_import()
    conflict = _existing_row(pending.rows[0])
    conflict["current_value"] = "9999"

    with patch("app.services.report_import_service.repositories.get_readings_by_batch", return_value=[conflict]), \
         patch("app.services.report_import_service.repositories.get_batch_by_id", return_value={"status": "collecting"}), \
         patch("app.services.report_import_service.repositories.append_batch") as mock_append_batch, \
         patch("app.services.report_import_service.repositories.append_reading") as mock_append_reading, \
         patch("app.services.report_import_service.repositories.update_batch_confirmed_count") as mock_update_count, \
         patch("app.services.report_import_service.repositories.update_batch_status") as mock_update_status, \
         patch("app.services.report_import_service.generate_report_image") as mock_generate:
        result = confirm_report_import("U1", pending, line_user_id="Uadmin")

    assert result.success is False
    assert result.duplicate is True
    mock_append_batch.assert_not_called()
    mock_append_reading.assert_not_called()
    mock_update_count.assert_not_called()
    mock_update_status.assert_not_called()
    mock_generate.assert_not_called()
