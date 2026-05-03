import logging

import gspread
from google.oauth2.service_account import Credentials

from app.config import settings
from app.storage.schema import TAB_HEADERS

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_tab_headers = TAB_HEADERS


class SheetsClient:
    def __init__(self):
        self._gc: gspread.Client | None = None
        self._spreadsheet: gspread.Spreadsheet | None = None
        self._worksheets: dict[str, gspread.Worksheet] = {}

    def _get_gc(self) -> gspread.Client:
        if self._gc is None:
            creds = Credentials.from_service_account_file(
                settings.GOOGLE_APPLICATION_CREDENTIALS, scopes=SCOPES
            )
            self._gc = gspread.authorize(creds)
        return self._gc

    def _get_spreadsheet(self) -> gspread.Spreadsheet:
        if self._spreadsheet is None:
            gc = self._get_gc()
            self._spreadsheet = gc.open_by_key(settings.GOOGLE_SHEETS_SPREADSHEET_ID)
        return self._spreadsheet

    def get_worksheet(self, tab_name: str) -> gspread.Worksheet:
        if tab_name in self._worksheets:
            return self._worksheets[tab_name]

        spreadsheet = self._get_spreadsheet()
        try:
            worksheet = spreadsheet.worksheet(tab_name)
        except gspread.WorksheetNotFound:
            raise ValueError(f"Tab '{tab_name}' not found in spreadsheet")
        self._worksheets[tab_name] = worksheet
        return worksheet

    def read_all(self, tab_name: str) -> list[dict]:
        ws = self.get_worksheet(tab_name)
        records = ws.get_all_records()
        logger.info("Read %d rows from tab '%s'", len(records), tab_name)
        return records

    def get_active_meters(self) -> list[dict]:
        rows = self.read_all("meters")
        return [r for r in rows if str(r.get("active", "")).upper() == "TRUE"]

    def get_meter_by_id(self, meter_id: str) -> dict | None:
        for m in self.get_active_meters():
            if m.get("meter_id") == meter_id:
                return m
        return None

    def append_row(self, tab_name: str, row: dict) -> None:
        ws = self.get_worksheet(tab_name)
        headers = _tab_headers.get(tab_name)
        if not headers:
            raise ValueError(f"Unknown tab '{tab_name}', no headers defined")
        values = [row.get(h, "") for h in headers]
        ws.append_row(values)
        logger.info("Appended row to tab '%s'", tab_name)

    def upsert_row(self, tab_name: str, key_column: str, row: dict) -> str:
        ws = self.get_worksheet(tab_name)
        headers = _tab_headers.get(tab_name)
        if not headers:
            raise ValueError(f"Unknown tab '{tab_name}', no headers defined")
        if key_column not in headers:
            raise ValueError(f"Unknown key column '{key_column}' for tab '{tab_name}'")

        key_value = str(row.get(key_column, ""))
        values = [row.get(h, "") for h in headers]
        key_col = headers.index(key_column) + 1
        cells = ws.findall(key_value, in_column=key_col)
        if not cells:
            ws.append_row(values)
            logger.info("Appended row to tab '%s' during upsert", tab_name)
            return "appended"

        target_row = cells[0].row
        for col, value in enumerate(values, start=1):
            ws.update_cell(target_row, col, value)
        logger.info("Updated tab '%s' row %d during upsert", tab_name, target_row)
        return "updated"

    def find_rows(self, tab_name: str, column: str, value: str) -> list[dict]:
        rows = self.read_all(tab_name)
        return [r for r in rows if str(r.get(column, "")) == str(value)]

    def update_cell(self, tab_name: str, row: int, col: int, value) -> None:
        ws = self.get_worksheet(tab_name)
        ws.update_cell(row, col, value)
        logger.info("Updated tab '%s' cell (%d,%d)", tab_name, row, col)

    def setup_tabs(self) -> None:
        spreadsheet = self._get_spreadsheet()
        existing = {ws.title for ws in spreadsheet.worksheets()}

        for tab_name, headers in _tab_headers.items():
            if tab_name in existing:
                logger.info("Tab '%s' already exists, skipping", tab_name)
                continue
            ws = spreadsheet.add_worksheet(title=tab_name, rows=1, cols=len(headers))
            ws.append_row(headers)
            logger.info("Created tab '%s' with headers", tab_name)


sheets_client = SheetsClient()
