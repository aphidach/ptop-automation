from unittest.mock import patch

from app.services import history_service


@patch("app.services.history_service.repositories")
def test_batch_summary_uses_saved_reading_totals(mock_repo):
    mock_repo.get_batch_by_id.return_value = {
        "batch_id": "2026-W19-U1",
        "week": "2026-W19",
        "status": "collecting",
        "expected_meter_count": "8",
    }
    mock_repo.get_readings_by_batch.return_value = [
        {"meter_id": "M1", "produced_unit": "508", "amount": "2133.6"},
        {"meter_id": "M2", "produced_unit": "410", "amount": "1722"},
    ]

    summary = history_service.get_batch_summary("2026-W19-U1")

    assert summary.confirmed_meter_count == 2
    assert summary.produced_unit == 918
    assert str(summary.amount) == "3855.6"
    assert "M3" in summary.missing_meter_ids


@patch("app.services.history_service.repositories")
def test_latest_report_prefers_batch_with_report_url(mock_repo):
    mock_repo.get_batches_by_source.return_value = [
        {"batch_id": "2026-W19-U1", "report_image_url": ""},
        {"batch_id": "2026-W18-U1", "report_image_url": "https://example.com/r.png"},
    ]

    assert history_service.get_latest_report_batch_id("U1") == "2026-W18-U1"
