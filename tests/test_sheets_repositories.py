from unittest.mock import MagicMock, patch

from app.sheets import repositories


def test_append_pending_confirmation_uses_pending_tab():
    row = {
        "confirmation_id": "cnf_1",
        "line_source_id": "U1",
        "meter_id": "M1",
        "status": "pending",
    }

    with patch("app.sheets.repositories.sheets_client") as mock_sheets_client:
        repositories.append_pending_confirmation(row)

    mock_sheets_client.append_row.assert_called_once_with("pending_confirmations", row)


def test_get_latest_pending_confirmation_filters_status_and_sorts_by_created_at():
    with patch("app.sheets.repositories.sheets_client") as mock_sheets_client:
        mock_sheets_client.find_rows.return_value = [
            {"confirmation_id": "cnf_old", "status": "pending", "created_at": "2026-05-01T00:00:00+00:00"},
            {"confirmation_id": "cnf_confirmed", "status": "confirmed", "created_at": "2026-05-03T00:00:00+00:00"},
            {"confirmation_id": "cnf_new", "status": "pending", "created_at": "2026-05-02T00:00:00+00:00"},
        ]

        row = repositories.get_latest_pending_confirmation("U1")

    mock_sheets_client.find_rows.assert_called_once_with("pending_confirmations", "line_source_id", "U1")
    assert row["confirmation_id"] == "cnf_new"


def test_update_pending_confirmation_status_updates_status_column():
    ws = MagicMock()
    ws.row_values.return_value = [
        "confirmation_id",
        "line_source_id",
        "line_user_id",
        "meter_id",
        "batch_id",
        "image_message_id",
        "ocr_value",
        "ocr_raw_text",
        "status",
        "expires_at",
        "created_at",
    ]
    cell = MagicMock()
    cell.row = 4
    ws.findall.return_value = [cell]

    with patch("app.sheets.repositories.sheets_client") as mock_sheets_client:
        mock_sheets_client.get_worksheet.return_value = ws

        updated = repositories.update_pending_confirmation_status("cnf_1", "confirmed")

    assert updated is True
    ws.findall.assert_called_once_with("cnf_1", in_column=1)
    ws.update_cell.assert_called_once_with(4, 9, "confirmed")


def test_update_batch_report_image_url_updates_url_and_timestamp():
    ws = MagicMock()
    ws.row_values.return_value = [
        "batch_id",
        "week",
        "date",
        "line_source_id",
        "expected_meter_count",
        "confirmed_meter_count",
        "status",
        "report_image_url",
        "created_at",
        "updated_at",
    ]
    cell = MagicMock()
    cell.row = 3
    ws.findall.return_value = [cell]

    with patch("app.sheets.repositories.sheets_client") as mock_sheets_client, \
         patch("app.sheets.repositories.datetime") as mock_datetime:
        mock_sheets_client.get_worksheet.return_value = ws
        mock_datetime.now.return_value.isoformat.return_value = "2026-05-02T00:00:00+00:00"

        repositories.update_batch_report_image_url(
            "2026-W19-U1",
            "https://cdn.example.com/reports/2026-W19-U1.png",
        )

    ws.findall.assert_called_once_with("2026-W19-U1", in_column=1)
    ws.update_cell.assert_any_call(3, 8, "https://cdn.example.com/reports/2026-W19-U1.png")
    ws.update_cell.assert_any_call(3, 10, "2026-05-02T00:00:00+00:00")

def test_update_setting_updates_existing_key():
    ws = MagicMock()
    ws.row_values.return_value = ["key", "value", "notes"]
    cell = MagicMock()
    cell.row = 4
    ws.findall.return_value = [cell]

    with patch("app.sheets.repositories.sheets_client") as mock_sheets_client:
        mock_sheets_client.get_worksheet.return_value = ws

        repositories.update_setting("default_rate", "4.5")

    ws.findall.assert_called_once_with("default_rate", in_column=1)
    ws.update_cell.assert_called_once_with(4, 2, "4.5")

def test_update_setting_appends_missing_key():
    ws = MagicMock()
    ws.row_values.return_value = ["key", "value", "notes"]
    ws.findall.return_value = []

    with patch("app.sheets.repositories.sheets_client") as mock_sheets_client:
        mock_sheets_client.get_worksheet.return_value = ws

        repositories.update_setting("report_title", "Solar Weekly Report")

    mock_sheets_client.append_row.assert_called_once_with(
        "settings",
        {"key": "report_title", "value": "Solar Weekly Report", "notes": ""},
    )
