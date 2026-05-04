import logging
from datetime import datetime, timezone

from app.config import settings
from app.sheets.client import sheets_client
from app.storage.sync import enqueue_outbox
from app.storage.sqlite import sqlite_client

logger = logging.getLogger(__name__)


def _use_sqlite() -> bool:
    return settings.STORAGE_BACKEND.strip().lower() == "sqlite"


def _row_client():
    return sqlite_client if _use_sqlite() else sheets_client


def _enqueue_if_sqlite(table_name: str, row: dict | None) -> None:
    if not _use_sqlite() or not row:
        return
    try:
        enqueue_outbox(table_name, row)
    except Exception:
        logger.exception("Failed to enqueue %s row for Google Sheets sync", table_name)


def _sqlite_first_row(tab_name: str, column: str, value: str) -> dict | None:
    rows = sqlite_client.find_rows(tab_name, column, value)
    return rows[0] if rows else None


def get_active_meters() -> list[dict]:
    return _row_client().get_active_meters()


def get_meter_by_id(meter_id: str) -> dict | None:
    return _row_client().get_meter_by_id(meter_id)


def get_latest_reading(meter_id: str, line_source_id: str | None = None) -> dict | None:
    rows = get_readings_by_meter(meter_id, line_source_id)
    if not rows:
        return None
    return rows[0]


def append_reading(reading: dict) -> None:
    _row_client().append_row("readings", reading)
    _enqueue_if_sqlite("readings", reading)
    logger.info("Appended reading: %s/%s", reading.get("meter_id"), reading.get("reading_id"))


def upsert_reading(reading: dict) -> None:
    reading_id = str(reading.get("reading_id", "")).strip()
    if not reading_id:
        append_reading(reading)
        return

    if _use_sqlite():
        updated = sqlite_client.update_rows("readings", "reading_id", reading_id, reading)
        if not updated:
            sqlite_client.append_row("readings", reading)
        _enqueue_if_sqlite("readings", reading)
        logger.info("Upserted reading: %s/%s", reading.get("meter_id"), reading_id)
        return

    sheets_client.upsert_row("readings", "reading_id", reading)
    logger.info("Upserted reading: %s/%s", reading.get("meter_id"), reading_id)


def get_readings_by_batch(batch_id: str) -> list[dict]:
    return _row_client().find_rows("readings", "batch_id", batch_id)


def get_all_readings() -> list[dict]:
    rows = _row_client().read_all("readings")
    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return rows


def get_readings_by_source(line_source_id: str) -> list[dict]:
    rows = _row_client().find_rows("readings", "line_source_id", line_source_id)
    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return rows


def get_readings_by_meter(meter_id: str, line_source_id: str | None = None) -> list[dict]:
    rows = _row_client().find_rows("readings", "meter_id", meter_id)
    if line_source_id:
        rows = [r for r in rows if str(r.get("line_source_id", "")) == str(line_source_id)]
    rows.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return rows


def get_batch_by_id(batch_id: str) -> dict | None:
    rows = _row_client().find_rows("batches", "batch_id", batch_id)
    if not rows:
        return None
    return rows[0]


def append_pending_confirmation(row: dict) -> None:
    _row_client().append_row("pending_confirmations", row)
    _enqueue_if_sqlite("pending_confirmations", row)
    logger.info("Appended pending confirmation: %s", row.get("confirmation_id"))


def get_latest_pending_confirmation(line_source_id: str) -> dict | None:
    rows = _row_client().find_rows("pending_confirmations", "line_source_id", line_source_id)
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
    if _use_sqlite():
        updated = sqlite_client.update_rows(
            "pending_confirmations",
            "confirmation_id",
            confirmation_id,
            {"status": status},
        )
        if not updated:
            logger.warning("Pending confirmation '%s' not found for status update", confirmation_id)
            return False
        _enqueue_if_sqlite(
            "pending_confirmations",
            _sqlite_first_row("pending_confirmations", "confirmation_id", confirmation_id),
        )
        logger.info("Updated pending confirmation '%s' status to '%s'", confirmation_id, status)
        return True

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
    rows = _row_client().find_rows("batches", "line_source_id", line_source_id)
    return _sort_batches(rows)


def get_all_batches() -> list[dict]:
    return _sort_batches(_row_client().read_all("batches"))


def _sort_batches(rows: list[dict]) -> list[dict]:
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
    _row_client().append_row("batches", batch)
    _enqueue_if_sqlite("batches", batch)
    logger.info("Appended batch: %s", batch.get("batch_id"))


def update_batch_status(batch_id: str, status: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    if _use_sqlite():
        updated = sqlite_client.update_rows(
            "batches",
            "batch_id",
            batch_id,
            {"status": status, "updated_at": now},
        )
        if not updated:
            logger.warning("Batch '%s' not found for status update", batch_id)
            return
        _enqueue_if_sqlite("batches", _sqlite_first_row("batches", "batch_id", batch_id))
        logger.info("Updated batch '%s' status to '%s'", batch_id, status)
        return

    ws = sheets_client.get_worksheet("batches")
    headers = ws.row_values(1)
    col_batch_id = headers.index("batch_id") + 1
    col_status = headers.index("status") + 1
    col_updated_at = headers.index("updated_at") + 1

    cells = ws.findall(batch_id, in_column=col_batch_id)
    if not cells:
        logger.warning("Batch '%s' not found for status update", batch_id)
        return

    for cell in cells:
        ws.update_cell(cell.row, col_status, status)
        ws.update_cell(cell.row, col_updated_at, now)
    logger.info("Updated batch '%s' status to '%s'", batch_id, status)


def update_batch_report_image_url(batch_id: str, report_image_url: str) -> None:
    now = datetime.now(timezone.utc).isoformat()
    if _use_sqlite():
        updated = sqlite_client.update_rows(
            "batches",
            "batch_id",
            batch_id,
            {"report_image_url": report_image_url, "updated_at": now},
        )
        if not updated:
            logger.warning("Batch '%s' not found for report image URL update", batch_id)
            return
        _enqueue_if_sqlite("batches", _sqlite_first_row("batches", "batch_id", batch_id))
        logger.info("Updated batch '%s' report_image_url", batch_id)
        return

    ws = sheets_client.get_worksheet("batches")
    headers = ws.row_values(1)
    col_batch_id = headers.index("batch_id") + 1
    col_report_image_url = headers.index("report_image_url") + 1
    col_updated_at = headers.index("updated_at") + 1

    cells = ws.findall(batch_id, in_column=col_batch_id)
    if not cells:
        logger.warning("Batch '%s' not found for report image URL update", batch_id)
        return

    for cell in cells:
        ws.update_cell(cell.row, col_report_image_url, report_image_url)
        ws.update_cell(cell.row, col_updated_at, now)
    logger.info("Updated batch '%s' report_image_url", batch_id)


def update_batch_confirmed_count(batch_id: str, count: int) -> None:
    now = datetime.now(timezone.utc).isoformat()
    if _use_sqlite():
        updated = sqlite_client.update_rows(
            "batches",
            "batch_id",
            batch_id,
            {"confirmed_meter_count": count, "updated_at": now},
        )
        if not updated:
            logger.warning("Batch '%s' not found for count update", batch_id)
            return
        _enqueue_if_sqlite("batches", _sqlite_first_row("batches", "batch_id", batch_id))
        logger.info("Updated batch '%s' confirmed_meter_count to %d", batch_id, count)
        return

    ws = sheets_client.get_worksheet("batches")
    headers = ws.row_values(1)
    col_batch_id = headers.index("batch_id") + 1
    col_confirmed = headers.index("confirmed_meter_count") + 1
    col_updated_at = headers.index("updated_at") + 1

    cells = ws.findall(batch_id, in_column=col_batch_id)
    if not cells:
        logger.warning("Batch '%s' not found for count update", batch_id)
        return

    for cell in cells:
        ws.update_cell(cell.row, col_confirmed, count)
        ws.update_cell(cell.row, col_updated_at, now)
    logger.info("Updated batch '%s' confirmed_meter_count to %d", batch_id, count)


def append_audit_log(row: dict) -> None:
    _row_client().append_row("audit_log", row)
    _enqueue_if_sqlite("audit_log", row)
    logger.info("Appended audit log: %s", row.get("event_id"))


def get_settings() -> dict[str, str]:
    rows = _row_client().read_all("settings")
    return {
        str(row.get("key", "")).strip(): str(row.get("value", "")).strip()
        for row in rows
        if str(row.get("key", "")).strip()
    }


def update_setting(key: str, value: str) -> None:
    if _use_sqlite():
        updated = sqlite_client.update_rows("settings", "key", key, {"value": value})
        if updated:
            _enqueue_if_sqlite("settings", _sqlite_first_row("settings", "key", key))
            logger.info("Updated setting '%s'", key)
            return
        row = {"key": key, "value": value, "notes": ""}
        sqlite_client.append_row("settings", row)
        _enqueue_if_sqlite("settings", row)
        logger.info("Appended setting '%s'", key)
        return

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
