import logging
from datetime import datetime, timezone

from app.sheets.client import sheets_client

logger = logging.getLogger(__name__)


def get_active_meters() -> list[dict]:
    return sheets_client.get_active_meters()


def get_meter_by_id(meter_id: str) -> dict | None:
    return sheets_client.get_meter_by_id(meter_id)


def get_latest_reading(meter_id: str) -> dict | None:
    rows = sheets_client.find_rows("readings", "meter_id", meter_id)
    if not rows:
        return None
    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return rows[0]


def append_reading(reading: dict) -> None:
    sheets_client.append_row("readings", reading)
    logger.info("Appended reading: %s/%s", reading.get("meter_id"), reading.get("reading_id"))


def get_readings_by_batch(batch_id: str) -> list[dict]:
    return sheets_client.find_rows("readings", "batch_id", batch_id)


def get_batch_by_id(batch_id: str) -> dict | None:
    rows = sheets_client.find_rows("batches", "batch_id", batch_id)
    if not rows:
        return None
    return rows[0]


def append_batch(batch: dict) -> None:
    sheets_client.append_row("batches", batch)
    logger.info("Appended batch: %s", batch.get("batch_id"))


def update_batch_status(batch_id: str, status: str) -> None:
    ws = sheets_client.get_worksheet("batches")
    headers = ws.row_values(1)
    col_batch_id = headers.index("batch_id") + 1
    col_status = headers.index("status") + 1
    col_updated_at = headers.index("updated_at") + 1

    cells = ws.findall(batch_id, in_column=col_batch_id)
    if not cells:
        logger.warning("Batch '%s' not found for status update", batch_id)
        return

    now = datetime.now(timezone.utc).isoformat()
    for cell in cells:
        ws.update_cell(cell.row, col_status, status)
        ws.update_cell(cell.row, col_updated_at, now)
    logger.info("Updated batch '%s' status to '%s'", batch_id, status)


def update_batch_confirmed_count(batch_id: str, count: int) -> None:
    ws = sheets_client.get_worksheet("batches")
    headers = ws.row_values(1)
    col_batch_id = headers.index("batch_id") + 1
    col_confirmed = headers.index("confirmed_meter_count") + 1
    col_updated_at = headers.index("updated_at") + 1

    cells = ws.findall(batch_id, in_column=col_batch_id)
    if not cells:
        logger.warning("Batch '%s' not found for count update", batch_id)
        return

    now = datetime.now(timezone.utc).isoformat()
    for cell in cells:
        ws.update_cell(cell.row, col_confirmed, count)
        ws.update_cell(cell.row, col_updated_at, now)
    logger.info("Updated batch '%s' confirmed_meter_count to %d", batch_id, count)


def append_audit_log(row: dict) -> None:
    sheets_client.append_row("audit_log", row)
    logger.info("Appended audit log: %s", row.get("event_id"))
