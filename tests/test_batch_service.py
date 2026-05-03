from unittest.mock import patch
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.services.batch_service import (
    BatchProgress,
    build_progress_message,
    generate_batch_id,
    get_batch_progress,
    get_or_create_batch,
    update_batch_after_reading,
)


@patch("app.services.batch_service.repositories")
class TestGenerateBatchId:
    def test_format_contains_week_and_source(self, mock_repo):
        batch_id = generate_batch_id("Uabc123")
        assert "Uabc123" in batch_id
        assert "-W" in batch_id
        parts = batch_id.split("-")
        assert len(parts) >= 3

    def test_different_sources_different_ids(self, mock_repo):
        id1 = generate_batch_id("U1")
        id2 = generate_batch_id("U2")
        assert id1 != id2

    def test_uses_configured_timezone_for_monday_after_midnight(self, mock_repo):
        bangkok_now = datetime(2026, 5, 4, 1, 27, tzinfo=ZoneInfo("Asia/Bangkok"))

        with patch("app.services.batch_service._now", return_value=bangkok_now):
            batch_id = generate_batch_id("U1")

        assert batch_id == "2026-W19-U1"


@patch("app.services.batch_service.repositories")
class TestGetOrCreateBatch:
    def test_creates_new_batch(self, mock_repo):
        mock_repo.get_batch_by_id.return_value = None
        result = get_or_create_batch("2026-W19-U1", "U1")
        mock_repo.append_batch.assert_called_once()
        assert result["batch_id"] == "2026-W19-U1"
        assert result["status"] == "collecting"
        assert result["confirmed_meter_count"] == "0"

    def test_creates_new_batch_with_expected_count_from_settings_sheet(self, mock_repo):
        mock_repo.get_batch_by_id.return_value = None
        mock_repo.get_settings.return_value = {"expected_meter_count": "6"}

        result = get_or_create_batch("2026-W19-U1", "U1")

        assert result["expected_meter_count"] == "6"

    def test_created_batch_uses_configured_timezone_week_and_date(self, mock_repo):
        mock_repo.get_batch_by_id.return_value = None
        bangkok_now = datetime(2026, 5, 4, 1, 27, tzinfo=ZoneInfo("Asia/Bangkok"))

        with patch("app.services.batch_service._now", return_value=bangkok_now):
            result = get_or_create_batch("2026-W19-U1", "U1")

        assert result["week"] == "2026-W19"
        assert result["date"] == "2026-05-04"

    def test_returns_existing_batch(self, mock_repo):
        existing = {"batch_id": "2026-W19-U1", "status": "collecting"}
        mock_repo.get_batch_by_id.return_value = existing
        result = get_or_create_batch("2026-W19-U1", "U1")
        mock_repo.append_batch.assert_not_called()
        assert result == existing


@patch("app.services.batch_service.repositories")
class TestGetBatchProgress:
    def test_progress_with_no_readings(self, mock_repo):
        mock_repo.get_batch_by_id.return_value = {
            "batch_id": "2026-W19-U1",
            "week": "2026-W19",
            "status": "collecting",
        }
        mock_repo.get_readings_by_batch.return_value = []
        progress = get_batch_progress("2026-W19-U1")
        assert progress.confirmed_meter_count == 0
        assert progress.expected_meter_count == 8
        assert len(progress.missing_meter_ids) == 8

    def test_progress_uses_expected_count_from_settings_sheet(self, mock_repo):
        mock_repo.get_batch_by_id.return_value = {
            "batch_id": "2026-W19-U1",
            "week": "2026-W19",
            "status": "collecting",
        }
        mock_repo.get_settings.return_value = {"expected_meter_count": "6"}
        mock_repo.get_readings_by_batch.return_value = []

        progress = get_batch_progress("2026-W19-U1")

        assert progress.expected_meter_count == 6

    def test_progress_with_some_readings(self, mock_repo):
        mock_repo.get_batch_by_id.return_value = {
            "batch_id": "2026-W19-U1",
            "week": "2026-W19",
            "status": "collecting",
        }
        mock_repo.get_readings_by_batch.return_value = [
            {"meter_id": "M1"},
            {"meter_id": "M2"},
            {"meter_id": "M3"},
        ]
        progress = get_batch_progress("2026-W19-U1")
        assert progress.confirmed_meter_count == 3
        assert "M4" in progress.missing_meter_ids
        assert "M1" not in progress.missing_meter_ids

    def test_progress_with_all_readings(self, mock_repo):
        mock_repo.get_batch_by_id.return_value = {
            "batch_id": "2026-W19-U1",
            "week": "2026-W19",
            "status": "collecting",
        }
        mock_repo.get_readings_by_batch.return_value = [
            {"meter_id": f"M{i}"} for i in range(1, 9)
        ]
        progress = get_batch_progress("2026-W19-U1")
        assert progress.confirmed_meter_count == 8
        assert progress.missing_meter_ids == []

    def test_progress_batch_not_found(self, mock_repo):
        mock_repo.get_batch_by_id.return_value = None
        progress = get_batch_progress("nonexistent")
        assert progress is None

    def test_duplicate_meter_counted_once(self, mock_repo):
        mock_repo.get_batch_by_id.return_value = {
            "batch_id": "2026-W19-U1",
            "week": "2026-W19",
            "status": "collecting",
        }
        mock_repo.get_readings_by_batch.return_value = [
            {"meter_id": "M1"},
            {"meter_id": "M1"},
            {"meter_id": "M2"},
        ]
        progress = get_batch_progress("2026-W19-U1")
        assert progress.confirmed_meter_count == 2


@patch("app.services.batch_service.repositories")
class TestUpdateBatchAfterReading:
    def test_updates_confirmed_count(self, mock_repo):
        mock_repo.get_batch_by_id.return_value = {
            "batch_id": "2026-W19-U1",
            "week": "2026-W19",
            "status": "collecting",
        }
        mock_repo.get_readings_by_batch.return_value = [
            {"meter_id": f"M{i}"} for i in range(1, 4)
        ]
        progress = update_batch_after_reading("2026-W19-U1")
        mock_repo.update_batch_confirmed_count.assert_called_once_with("2026-W19-U1", 3)
        assert progress.confirmed_meter_count == 3
        assert progress.status == "collecting"

    def test_marks_complete_when_all_confirmed(self, mock_repo):
        mock_repo.get_batch_by_id.return_value = {
            "batch_id": "2026-W19-U1",
            "week": "2026-W19",
            "status": "collecting",
        }
        mock_repo.get_readings_by_batch.return_value = [
            {"meter_id": f"M{i}"} for i in range(1, 9)
        ]
        progress = update_batch_after_reading("2026-W19-U1")
        mock_repo.update_batch_status.assert_called_once_with("2026-W19-U1", "complete")
        assert progress.status == "complete"

    def test_batch_not_found_returns_fallback(self, mock_repo):
        mock_repo.get_batch_by_id.return_value = None
        progress = update_batch_after_reading("nonexistent")
        assert progress.status == "unknown"
        assert progress.confirmed_meter_count == 0


@patch("app.services.batch_service.repositories")
class TestBuildProgressMessage:
    def test_missing_meters_message(self, mock_repo):
        mock_repo.get_batch_by_id.return_value = {
            "batch_id": "2026-W19-U1",
            "week": "2026-W19",
            "status": "collecting",
        }
        mock_repo.get_readings_by_batch.return_value = [
            {"meter_id": "M1"},
            {"meter_id": "M2"},
            {"meter_id": "M3"},
        ]
        msg = build_progress_message("2026-W19-U1")
        assert "3/8" in msg
        assert "M4" in msg

    def test_complete_message(self, mock_repo):
        mock_repo.get_batch_by_id.return_value = {
            "batch_id": "2026-W19-U1",
            "week": "2026-W19",
            "status": "complete",
        }
        mock_repo.get_readings_by_batch.return_value = [
            {"meter_id": f"M{i}"} for i in range(1, 9)
        ]
        msg = build_progress_message("2026-W19-U1")
        assert "8/8" in msg
        assert "ครบ" in msg

    def test_batch_not_found(self, mock_repo):
        mock_repo.get_batch_by_id.return_value = None
        msg = build_progress_message("nonexistent")
        assert "ไม่พบ" in msg
