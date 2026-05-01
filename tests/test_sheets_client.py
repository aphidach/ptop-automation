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
