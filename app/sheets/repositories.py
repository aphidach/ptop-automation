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


def get_readings_by_meter(meter_id: str, line_source_id: str | None = None) -> list[dict]:
    rows = sheets_client.find_rows("readings", "meter_id", meter_id)
    if line_source_id:
        rows = [r for r in rows if str(r.get("line_source_id", "")) == str(line_source_id)]
    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return rows


def get_batch_by_id(batch_id: str) -> dict | None:
    rows = sheets_client.find_rows("batches", "batch_id", batch_id)
    if not rows:
        return None
    return rows[0]


def append_pending_confirmation(row: dict) -> None:
    sheets_client.append_row("pending_confirmations", row)
    logger.info("Appended pending confirmation: %s", row.get("confirmation_id"))


def get_latest_pending_confirmation(line_source_id: str) -> dict | None:
    rows = sheets_client.find_rows("pending_confirmations", "line_source_id", line_source_id)
    pending_rows = [
        row
        for row in rows
        if str(row.get("status", "")).strip().lower() == "pending"
    ]
    if not pending_rows:
        return None
    pending_rows.sort(
        key=lambda row: (
            str(row.get("created_at", "")),
            str(row.get("confirmation_id", "")),
        ),
        reverse=True,
    )
    return pending_rows[0]


def update_pending_confirmation_status(confirmation_id: str, status: str) -> bool:
    ws = sheets_client.get_worksheet("pending_confirmations")
    headers = ws.row_values(1)
    col_confirmation_id = headers.index("confirmation_id") + 1
    col_status = headers.index("status") + 1

    cells = ws.findall(confirmation_id, in_column=col_confirmation_id)
    if not cells:
        logger.warning("Pending confirmation '%s' not found for status update", confirmation_id)
        return False

    for cell in cells:
        ws.update_cell(cell.row, col_status, status)
    logger.info("Updated pending confirmation '%s' status to '%s'", confirmation_id, status)
    return True


def get_batches_by_source(line_source_id: str) -> list[dict]:
    rows = sheets_client.find_rows("batches", "line_source_id", line_source_id)
    rows.sort(
        key=lambda r: (
            str(r.get("week", "")),
            str(r.get("created_at", "")),
            str(r.get("batch_id", "")),
        ),
        reverse=True,
    )
    return rows


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


def update_batch_report_image_url(batch_id: str, report_image_url: str) -> None:
    ws = sheets_client.get_worksheet("batches")
    headers = ws.row_values(1)
    col_batch_id = headers.index("batch_id") + 1
    col_report_image_url = headers.index("report_image_url") + 1
    col_updated_at = headers.index("updated_at") + 1

    cells = ws.findall(batch_id, in_column=col_batch_id)
    if not cells:
        logger.warning("Batch '%s' not found for report image URL update", batch_id)
        return

    now = datetime.now(timezone.utc).isoformat()
    for cell in cells:
        ws.update_cell(cell.row, col_report_image_url, report_image_url)
        ws.update_cell(cell.row, col_updated_at, now)
    logger.info("Updated batch '%s' report_image_url", batch_id)


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


def get_settings() -> dict[str, str]:
    rows = sheets_client.read_all("settings")
    return {
        str(row.get("key", "")).strip(): str(row.get("value", "")).strip()
        for row in rows
        if str(row.get("key", "")).strip()
    }


def update_setting(key: str, value: str) -> None:
    ws = sheets_client.get_worksheet("settings")
    headers = ws.row_values(1)
    col_key = headers.index("key") + 1
    col_value = headers.index("value") + 1

    cells = ws.findall(key, in_column=col_key)
    if cells:
        for cell in cells:
            ws.update_cell(cell.row, col_value, value)
        logger.info("Updated setting '%s'", key)
        return

    sheets_client.append_row("settings", {"key": key, "value": value, "notes": ""})
    logger.info("Appended setting '%s'", key)
