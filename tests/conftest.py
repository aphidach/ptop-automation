import pytest

from app.config import settings
from app.storage import sync as storage_sync
from app.storage.sqlite import sqlite_client


@pytest.fixture(autouse=True)
def _isolate_sqlite_db(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "SQLITE_DB_PATH", str(tmp_path / "solar-meter-bot.db"))
    monkeypatch.setattr(settings, "SHEETS_SYNC_ENABLED", False)
    monkeypatch.setattr(settings, "SHEETS_STARTUP_PULL_ENABLED", True)
    monkeypatch.setattr(settings, "SHEETS_SYNC_INTERVAL_SECONDS", 600)
    monkeypatch.setattr(settings, "SHEETS_SYNC_BATCH_SIZE", 50)
    sqlite_client._is_setup = False
    storage_sync.sync_state.last_pull_at = ""
    storage_sync.sync_state.last_push_at = ""
    storage_sync.sync_state.last_error = ""
    storage_sync.sync_state.last_pull_error = ""
    storage_sync.sync_state.last_push_error = ""
    storage_sync.sheets_client = None
