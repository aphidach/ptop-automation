from unittest.mock import MagicMock

from app.sheets import repositories
from app.storage.schema import TAB_HEADERS
from app.storage import sync as storage_sync
from app.storage.sqlite import sqlite_client


def _use_sqlite(tmp_path, monkeypatch):
    monkeypatch.setattr(repositories.settings, "STORAGE_BACKEND", "sqlite")
    monkeypatch.setattr(repositories.settings, "SQLITE_DB_PATH", str(tmp_path / "test.db"))
    sqlite_client._is_setup = False


def test_startup_pull_replaces_business_config_from_sheets(tmp_path, monkeypatch):
    _use_sqlite(tmp_path, monkeypatch)

    def read_all(tab_name):
        return {
            "meters": [
                {
                    "meter_id": "M1",
                    "name": "Solar 1",
                    "location": "",
                    "sort_order": "1",
                    "active": "TRUE",
                    "default_rate": "4.2",
                }
            ],
            "settings": [{"key": "default_rate", "value": "4.5", "notes": ""}],
        }[tab_name]

    fake_sheets = MagicMock()
    fake_sheets.read_all.side_effect = read_all
    monkeypatch.setattr(storage_sync, "sheets_client", fake_sheets)

    assert storage_sync.pull_business_config_from_sheets() is True
    assert repositories.get_meter_by_id("M1")["name"] == "Solar 1"
    assert repositories.get_settings()["default_rate"] == "4.5"
    assert storage_sync.sync_state.last_pull_at


def test_startup_pull_clears_pending_settings_outbox(tmp_path, monkeypatch):
    _use_sqlite(tmp_path, monkeypatch)
    repositories.update_setting("default_rate", "9.9")
    assert sqlite_client.outbox_counts()["pending"] == 1

    fake_sheets = MagicMock()
    fake_sheets.read_all.side_effect = lambda tab_name: {
        "meters": [],
        "settings": [{"key": "default_rate", "value": "4.5", "notes": ""}],
    }[tab_name]
    monkeypatch.setattr(storage_sync, "sheets_client", fake_sheets)

    assert storage_sync.pull_business_config_from_sheets() is True

    assert repositories.get_settings()["default_rate"] == "4.5"
    assert sqlite_client.outbox_counts().get("pending", 0) == 0


def test_manual_pull_replaces_all_sqlite_tables_from_sheets(tmp_path, monkeypatch):
    _use_sqlite(tmp_path, monkeypatch)
    repositories.append_reading(
        {
            "reading_id": "local-reading",
            "batch_id": "2026-W19-U1",
            "line_source_id": "U1",
            "meter_id": "M1",
            "current_value": "100",
            "created_at": "2026-05-01T00:00:00+00:00",
        }
    )
    assert sqlite_client.outbox_counts()["pending"] == 1

    sheet_rows = {tab_name: [] for tab_name in TAB_HEADERS}
    sheet_rows["meters"] = [
        {
            "meter_id": "M1",
            "name": "Solar from Sheet",
            "location": "",
            "sort_order": "1",
            "active": "TRUE",
            "default_rate": "4.6",
        }
    ]
    sheet_rows["settings"] = [{"key": "default_rate", "value": "4.6", "notes": ""}]
    sheet_rows["readings"] = [
        {
            "reading_id": "sheet-reading",
            "batch_id": "2026-W18-U1",
            "line_source_id": "U1",
            "meter_id": "M1",
            "current_value": "120",
            "created_at": "2026-04-27T00:00:00+00:00",
        }
    ]

    fake_sheets = MagicMock()
    fake_sheets.read_all.side_effect = lambda tab_name: sheet_rows[tab_name]
    monkeypatch.setattr(storage_sync, "sheets_client", fake_sheets)

    assert storage_sync.pull_all_from_sheets() is True

    assert repositories.get_meter_by_id("M1")["name"] == "Solar from Sheet"
    assert repositories.get_settings()["default_rate"] == "4.6"
    assert sqlite_client.read_all("readings")[0]["reading_id"] == "sheet-reading"
    assert sqlite_client.outbox_counts().get("pending", 0) == 0
    assert fake_sheets.read_all.call_count == len(TAB_HEADERS)


def test_repository_writes_enqueue_sync_outbox(tmp_path, monkeypatch):
    _use_sqlite(tmp_path, monkeypatch)

    repositories.append_reading(
        {
            "reading_id": "rdg_1",
            "batch_id": "2026-W19-U1",
            "line_source_id": "U1",
            "meter_id": "M1",
            "current_value": "100",
            "created_at": "2026-05-01T00:00:00+00:00",
        }
    )

    outbox = sqlite_client.fetch_outbox(10)
    assert len(outbox) == 1
    assert outbox[0]["table_name"] == "readings"
    assert outbox[0]["row_key"] == "rdg_1"
    assert outbox[0]["status"] == "pending"


def test_sheets_backend_does_not_enqueue_sync_outbox(tmp_path, monkeypatch):
    monkeypatch.setattr(repositories.settings, "STORAGE_BACKEND", "sheets")
    monkeypatch.setattr(repositories.settings, "SQLITE_DB_PATH", str(tmp_path / "test.db"))
    repositories.sqlite_client._is_setup = False
    monkeypatch.setattr(repositories.sheets_client, "append_row", MagicMock())

    repositories.append_reading({"reading_id": "rdg_1", "meter_id": "M1"})

    assert sqlite_client.fetch_outbox(10) == []


def test_repeated_batch_updates_coalesce_to_latest_payload(tmp_path, monkeypatch):
    _use_sqlite(tmp_path, monkeypatch)
    repositories.append_batch(
        {
            "batch_id": "2026-W19-U1",
            "week": "2026-W19",
            "date": "2026-05-03",
            "line_source_id": "U1",
            "expected_meter_count": "8",
            "confirmed_meter_count": "0",
            "status": "collecting",
            "created_at": "2026-05-03T00:00:00+00:00",
            "updated_at": "2026-05-03T00:00:00+00:00",
        }
    )

    repositories.update_batch_confirmed_count("2026-W19-U1", 3)
    repositories.update_batch_status("2026-W19-U1", "complete")

    outbox = sqlite_client.fetch_outbox(10)
    assert len(outbox) == 1
    assert outbox[0]["table_name"] == "batches"
    assert '"confirmed_meter_count": "3"' in outbox[0]["payload_json"]
    assert '"status": "complete"' in outbox[0]["payload_json"]


def test_flush_outbox_syncs_to_sheets_and_marks_synced(tmp_path, monkeypatch):
    _use_sqlite(tmp_path, monkeypatch)
    mock_upsert = MagicMock(return_value="appended")
    fake_sheets = MagicMock()
    fake_sheets.upsert_row = mock_upsert
    monkeypatch.setattr(storage_sync, "sheets_client", fake_sheets)
    repositories.update_setting("default_rate", "4.5")

    synced = storage_sync.flush_outbox()

    assert synced == 1
    mock_upsert.assert_called_once()
    assert sqlite_client.outbox_counts().get("synced") == 1
    assert storage_sync.sync_state.last_push_at
    assert storage_sync.sync_state.last_error == ""


def test_flush_outbox_failure_marks_failed_and_successful_retry_marks_synced(tmp_path, monkeypatch):
    _use_sqlite(tmp_path, monkeypatch)
    repositories.update_setting("default_rate", "4.5")

    def fail(*args, **kwargs):
        raise RuntimeError("quota exceeded")

    fake_sheets = MagicMock()
    fake_sheets.upsert_row.side_effect = fail
    monkeypatch.setattr(storage_sync, "sheets_client", fake_sheets)
    assert storage_sync.flush_outbox() == 0
    assert sqlite_client.outbox_counts()["failed"] == 1
    assert storage_sync.sync_state.last_error == "quota exceeded"

    fake_sheets.upsert_row = MagicMock(return_value="updated")
    assert storage_sync.flush_outbox() == 1
    counts = sqlite_client.outbox_counts()
    assert counts.get("failed", 0) == 0
    assert counts["synced"] == 1


def test_empty_flush_keeps_startup_pull_error_visible(tmp_path, monkeypatch):
    _use_sqlite(tmp_path, monkeypatch)

    fake_sheets = MagicMock()
    fake_sheets.read_all.side_effect = RuntimeError("sheets down")
    monkeypatch.setattr(storage_sync, "sheets_client", fake_sheets)

    assert storage_sync.pull_business_config_from_sheets() is False
    assert storage_sync.flush_outbox() == 0

    assert storage_sync.health()["last_error"] == "sheets down"
