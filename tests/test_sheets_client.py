from unittest.mock import MagicMock

from app.sheets.client import SheetsClient


def test_get_worksheet_caches_by_tab_name():
    client = SheetsClient()
    spreadsheet = MagicMock()
    worksheet = MagicMock()
    spreadsheet.worksheet.return_value = worksheet
    client._spreadsheet = spreadsheet

    first = client.get_worksheet("readings")
    second = client.get_worksheet("readings")

    assert first is worksheet
    assert second is worksheet
    spreadsheet.worksheet.assert_called_once_with("readings")


def test_get_worksheet_caches_each_tab_separately():
    client = SheetsClient()
    spreadsheet = MagicMock()
    readings = MagicMock()
    batches = MagicMock()
    spreadsheet.worksheet.side_effect = [readings, batches]
    client._spreadsheet = spreadsheet

    assert client.get_worksheet("readings") is readings
    assert client.get_worksheet("batches") is batches

    assert spreadsheet.worksheet.call_count == 2


def test_upsert_row_appends_when_key_is_missing():
    client = SheetsClient()
    worksheet = MagicMock()
    worksheet.findall.return_value = []
    spreadsheet = MagicMock()
    spreadsheet.worksheet.return_value = worksheet
    client._spreadsheet = spreadsheet

    result = client.upsert_row(
        "settings",
        "key",
        {"key": "default_rate", "value": "4.5", "notes": ""},
    )

    assert result == "appended"
    worksheet.append_row.assert_called_once_with(["default_rate", "4.5", ""])


def test_upsert_row_updates_existing_key_row():
    client = SheetsClient()
    cell = MagicMock()
    cell.row = 4
    worksheet = MagicMock()
    worksheet.findall.return_value = [cell]
    spreadsheet = MagicMock()
    spreadsheet.worksheet.return_value = worksheet
    client._spreadsheet = spreadsheet

    result = client.upsert_row(
        "settings",
        "key",
        {"key": "default_rate", "value": "4.5", "notes": ""},
    )

    assert result == "updated"
    worksheet.update_cell.assert_any_call(4, 1, "default_rate")
    worksheet.update_cell.assert_any_call(4, 2, "4.5")
    worksheet.update_cell.assert_any_call(4, 3, "")
