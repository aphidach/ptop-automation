from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from app.config import settings
from app.storage.sqlite import sqlite_client

logger = logging.getLogger(__name__)

BUSINESS_PULL_TABLES = ("meters", "settings")
PUSH_ROW_KEYS = {
    "readings": "reading_id",
    "batches": "batch_id",
    "pending_confirmations": "confirmation_id",
    "settings": "key",
    "audit_log": "event_id",
}


@dataclass
class SyncState:
    last_pull_at: str = ""
    last_push_at: str = ""
    last_error: str = ""
    last_pull_error: str = ""
    last_push_error: str = ""


sync_state = SyncState()
sheets_client = None


def _sheets_client():
    global sheets_client
    if sheets_client is None:
        from app.sheets.client import sheets_client as client

        sheets_client = client
    return sheets_client


def enqueue_outbox(table_name: str, row: dict) -> None:
    key_column = PUSH_ROW_KEYS.get(table_name)
    if not key_column:
        return
    row_key = str(row.get(key_column, "")).strip()
    sqlite_client.enqueue_outbox(table_name, row_key, row)


def pull_business_config_from_sheets() -> bool:
    try:
        for table_name in BUSINESS_PULL_TABLES:
            sqlite_client.replace_all(table_name, _sheets_client().read_all(table_name))
        sqlite_client.delete_outbox_for_table("settings")
        sync_state.last_pull_at = _now()
        sync_state.last_pull_error = ""
        _refresh_last_error()
        logger.info("Pulled business config from Google Sheets")
        return True
    except Exception as exc:
        sync_state.last_pull_error = str(exc)
        _refresh_last_error()
        logger.exception("Failed to pull business config from Google Sheets")
        return False


def flush_outbox(batch_size: int | None = None) -> int:
    limit = batch_size or settings.SHEETS_SYNC_BATCH_SIZE
    synced = 0
    last_error = ""
    outbox_items = sqlite_client.fetch_outbox(limit)
    for item in outbox_items:
        table_name = str(item["table_name"])
        row_key = str(item["row_key"])
        key_column = PUSH_ROW_KEYS.get(table_name)
        if not key_column:
            sqlite_client.mark_outbox_synced(table_name, row_key)
            continue

        try:
            payload = json.loads(item["payload_json"])
            _sheets_client().upsert_row(table_name, key_column, payload)
            sqlite_client.mark_outbox_synced(table_name, row_key)
            synced += 1
        except Exception as exc:
            last_error = str(exc)
            sqlite_client.mark_outbox_failed(table_name, row_key, last_error)
            logger.exception("Failed to sync %s/%s to Google Sheets", table_name, row_key)

    if outbox_items:
        sync_state.last_push_at = _now()
        sync_state.last_push_error = last_error
        _refresh_last_error()
    return synced


def health() -> dict:
    counts = sqlite_client.outbox_counts()
    return {
        "enabled": settings.SHEETS_SYNC_ENABLED,
        "last_pull_at": sync_state.last_pull_at,
        "last_push_at": sync_state.last_push_at,
        "pending_count": counts.get("pending", 0),
        "failed_count": counts.get("failed", 0),
        "last_error": sync_state.last_error,
    }


async def periodic_sync_loop() -> None:
    while True:
        await asyncio.sleep(settings.SHEETS_SYNC_INTERVAL_SECONDS)
        await asyncio.to_thread(flush_outbox)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _refresh_last_error() -> None:
    sync_state.last_error = sync_state.last_push_error or sync_state.last_pull_error
