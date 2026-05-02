from unittest.mock import MagicMock, patch

from app.sheets import repositories


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
