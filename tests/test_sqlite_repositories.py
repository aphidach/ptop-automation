from app.sheets import repositories


def _use_sqlite(tmp_path, monkeypatch):
    monkeypatch.setattr(repositories.settings, "STORAGE_BACKEND", "sqlite")
    monkeypatch.setattr(repositories.settings, "SQLITE_DB_PATH", str(tmp_path / "test.db"))
    repositories.sqlite_client._is_setup = False


def test_sqlite_reads_and_updates_settings(tmp_path, monkeypatch):
    _use_sqlite(tmp_path, monkeypatch)

    repositories.update_setting("default_rate", "4.5")
    repositories.update_setting("expected_meter_count", "6")

    assert repositories.get_settings() == {
        "default_rate": "4.5",
        "expected_meter_count": "6",
    }

    repositories.update_setting("default_rate", "4.7")

    assert repositories.get_settings()["default_rate"] == "4.7"


def test_sqlite_latest_reading_uses_newest_created_at(tmp_path, monkeypatch):
    _use_sqlite(tmp_path, monkeypatch)

    repositories.append_reading(
        {
            "reading_id": "rdg_old",
            "batch_id": "2026-W18-U1",
            "line_source_id": "U1",
            "meter_id": "M1",
            "current_value": "100",
            "created_at": "2026-05-01T00:00:00+00:00",
        }
    )
    repositories.append_reading(
        {
            "reading_id": "rdg_new",
            "batch_id": "2026-W19-U1",
            "line_source_id": "U1",
            "meter_id": "M1",
            "current_value": "120",
            "created_at": "2026-05-02T00:00:00+00:00",
        }
    )

    latest = repositories.get_latest_reading("M1")

    assert latest["reading_id"] == "rdg_new"
    assert latest["current_value"] == "120"


def test_sqlite_batch_updates_preserve_hot_path_data(tmp_path, monkeypatch):
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
            "report_image_url": "",
            "created_at": "2026-05-03T00:00:00+00:00",
            "updated_at": "2026-05-03T00:00:00+00:00",
        }
    )

    repositories.update_batch_confirmed_count("2026-W19-U1", 3)
    repositories.update_batch_status("2026-W19-U1", "complete")
    repositories.update_batch_report_image_url("2026-W19-U1", "https://example.com/report.png")

    batch = repositories.get_batch_by_id("2026-W19-U1")

    assert batch["confirmed_meter_count"] == "3"
    assert batch["status"] == "complete"
    assert batch["report_image_url"] == "https://example.com/report.png"


def test_sqlite_pending_confirmation_status_transition(tmp_path, monkeypatch):
    _use_sqlite(tmp_path, monkeypatch)

    repositories.append_pending_confirmation(
        {
            "confirmation_id": "cnf_1",
            "line_source_id": "U1",
            "meter_id": "M1",
            "status": "pending",
            "created_at": "2026-05-02T00:00:00+00:00",
        }
    )

    assert repositories.get_latest_pending_confirmation("U1")["confirmation_id"] == "cnf_1"
    assert repositories.update_pending_confirmation_status("cnf_1", "confirmed") is True
    assert repositories.get_latest_pending_confirmation("U1") is None
