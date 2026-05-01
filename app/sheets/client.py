import logging

import gspread
from google.oauth2.service_account import Credentials

from app.config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_tab_headers = {
    "meters": ["meter_id", "name", "location", "sort_order", "active", "default_rate"],
    "readings": [
        "reading_id",
        "batch_id",
        "date",
        "week",
        "line_source_id",
        "line_user_id",
        "meter_id",
        "current_value",
        "last_value",
        "produced_unit",
        "rate",
        "amount",
        "ocr_raw_text",
        "ocr_value",
        "confirmation_method",
        "image_message_id",
        "image_file_id",
        "created_at",
    ],
    "batches": [
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
    ],
    "pending_confirmations": [
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
    ],
    "settings": ["key", "value", "notes"],
    "audit_log": [
        "event_id",
        "timestamp",
        "event_type",
        "line_source_id",
        "meter_id",
        "payload_json",
    ],
}


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
