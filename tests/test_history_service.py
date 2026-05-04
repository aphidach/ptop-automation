from unittest.mock import patch
from datetime import datetime, timezone

from app.services import history_service


@patch("app.services.history_service.repositories")
def test_batch_summary_uses_saved_reading_totals(mock_repo):
    mock_repo.get_batch_by_id.return_value = {
        "batch_id": "2026-W19-U1",
        "week": "2026-W19",
        "status": "collecting",
        "expected_meter_count": "8",
        "date": "2026-05-03",
        "created_at": "2026-05-03T01:00:00+00:00",
        "updated_at": "2026-05-03T02:00:00+00:00",
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
    assert summary.date == "2026-05-03"
    assert summary.created_at == "2026-05-03T01:00:00+00:00"
    assert summary.updated_at == "2026-05-03T02:00:00+00:00"


@patch("app.services.history_service.generate_batch_id", return_value="2026-W19-U1")
@patch("app.services.history_service.repositories")
def test_previous_batch_summary_skips_current_generated_batch(mock_repo, mock_generate_batch):
    mock_repo.get_batches_by_source.return_value = [
        {"batch_id": "2026-W19-U1", "week": "2026-W19", "line_source_id": "U1"},
        {"batch_id": "2026-W18-U1", "week": "2026-W18", "status": "complete", "expected_meter_count": "8", "line_source_id": "U1"},
    ]
    mock_repo.get_batch_by_id.return_value = {
        "batch_id": "2026-W18-U1",
        "week": "2026-W18",
        "status": "complete",
        "expected_meter_count": "8",
        "line_source_id": "U1",
    }
    mock_repo.get_readings_by_batch.return_value = [
        {"meter_id": "M1", "produced_unit": "508", "amount": "2133.6", "line_source_id": "U1"},
    ]

    summary = history_service.get_previous_batch_summary("U1")

    assert summary.batch_id == "2026-W18-U1"
    assert summary.week == "2026-W18"
    mock_generate_batch.assert_called_once_with("U1")


@patch("app.services.history_service.repositories")
def test_latest_report_prefers_batch_with_report_url(mock_repo):
    mock_repo.get_batches_by_source.return_value = [
        {"batch_id": "2026-W19-U1", "report_image_url": ""},
        {"batch_id": "2026-W18-U1", "report_image_url": "https://example.com/r.png"},
    ]

    assert history_service.get_latest_report_batch_id("U1") == "2026-W18-U1"


@patch("app.services.history_service.repositories")
def test_latest_report_skips_empty_current_batch_for_latest_complete(mock_repo):
    mock_repo.get_batches_by_source.return_value = [
        {
            "batch_id": "2026-W19-U1",
            "week": "2026-W19",
            "status": "collecting",
            "expected_meter_count": "8",
            "report_image_url": "",
        },
        {
            "batch_id": "2026-W18-U1",
            "week": "2026-W18",
            "status": "complete",
            "expected_meter_count": "8",
            "report_image_url": "",
        },
    ]

    def get_readings(batch_id):
        if batch_id == "2026-W19-U1":
            return []
        return [{"meter_id": f"M{i}"} for i in range(1, 9)]

    mock_repo.get_readings_by_batch.side_effect = get_readings

    assert history_service.get_latest_report_batch_id("U1") == "2026-W18-U1"


@patch("app.services.history_service.repositories")
def test_latest_report_returns_none_when_only_current_batch_is_empty(mock_repo):
    mock_repo.get_batches_by_source.return_value = [
        {
            "batch_id": "2026-W19-U1",
            "week": "2026-W19",
            "status": "collecting",
            "expected_meter_count": "8",
            "report_image_url": "",
        },
    ]
    mock_repo.get_readings_by_batch.return_value = []

    assert history_service.get_latest_report_batch_id("U1") is None


@patch("app.services.history_service.repositories")
def test_batch_summary_falls_back_to_readings_when_batch_row_is_missing(mock_repo):
    mock_repo.get_batch_by_id.return_value = None
    mock_repo.get_readings_by_batch.return_value = [
        {"meter_id": "M1", "week": "2026-W18", "produced_unit": "508", "amount": "2133.6"},
        {"meter_id": "M2", "week": "2026-W18", "produced_unit": "410", "amount": "1722"},
    ]

    summary = history_service.get_batch_summary("2026-W18-U1")

    assert summary.week == "2026-W18"
    assert summary.status == "collecting"
    assert summary.confirmed_meter_count == 2
    assert summary.produced_unit == 918


@patch("app.services.history_service.repositories")
def test_recent_batch_summaries_include_reading_only_batches_from_last_month(mock_repo):
    mock_repo.get_batches_by_source.return_value = [
        {"batch_id": "2026-W17-U1", "week": "2026-W17", "date": "2026-04-26", "line_source_id": "U1"},
        {"batch_id": "2026-W12-U1", "week": "2026-W12", "date": "2026-03-20", "line_source_id": "U1"},
    ]
    mock_repo.get_readings_by_source.return_value = [
        {"batch_id": "2026-W18-U1", "week": "2026-W18", "date": "2026-05-02", "meter_id": "M1", "line_source_id": "U1"},
        {"batch_id": "2026-W12-U1", "week": "2026-W12", "date": "2026-03-20", "meter_id": "M1", "line_source_id": "U1"},
    ]

    def get_batch(batch_id):
        rows = {
            "2026-W17-U1": {
                "batch_id": "2026-W17-U1",
                "week": "2026-W17",
                "status": "complete",
                "expected_meter_count": "8",
                "line_source_id": "U1",
            },
            "2026-W12-U1": {
                "batch_id": "2026-W12-U1",
                "week": "2026-W12",
                "status": "complete",
                "expected_meter_count": "8",
                "line_source_id": "U1",
            },
        }
        return rows.get(batch_id)

    def get_readings(batch_id):
        return [
            {"meter_id": "M1", "week": "2026-W18", "produced_unit": "1", "amount": "4.2", "line_source_id": "U1"}
        ] if batch_id == "2026-W18-U1" else []

    mock_repo.get_batch_by_id.side_effect = get_batch
    mock_repo.get_readings_by_batch.side_effect = get_readings

    summaries = history_service.get_recent_batch_summaries(
        "U1",
        now=datetime(2026, 5, 3, tzinfo=timezone.utc),
    )

    assert [summary.week for summary in summaries] == ["2026-W18", "2026-W17"]


@patch("app.services.history_service.repositories")
def test_recent_batch_summaries_can_include_all_sources_for_admin(mock_repo):
    mock_repo.get_all_batches.return_value = [
        {"batch_id": "2026-W18-U1", "week": "2026-W18", "date": "2026-05-01", "line_source_id": "U1"},
        {"batch_id": "2026-W18-U2", "week": "2026-W18", "date": "2026-05-02", "line_source_id": "U2"},
    ]
    mock_repo.get_all_readings.return_value = []

    def get_batch(batch_id):
        return {
            "batch_id": batch_id,
            "week": "2026-W18",
            "status": "complete",
            "expected_meter_count": "8",
            "line_source_id": batch_id.rsplit("-", 1)[-1],
        }

    mock_repo.get_batch_by_id.side_effect = get_batch
    mock_repo.get_readings_by_batch.return_value = [
        {"meter_id": "M1", "produced_unit": "1", "amount": "4.2"}
    ]

    summaries = history_service.get_recent_batch_summaries(
        None,
        now=datetime(2026, 5, 4, tzinfo=timezone.utc),
    )

    assert [summary.batch_id for summary in summaries] == ["2026-W18-U2", "2026-W18-U1"]


@patch("app.services.history_service.repositories")
def test_meter_history_filters_by_selected_period(mock_repo):
    mock_repo.get_readings_by_meter.return_value = [
        {
            "meter_id": "M1",
            "week": "2026-W18",
            "created_at": "2026-05-03T01:00:00+00:00",
        },
        {
            "meter_id": "M1",
            "week": "2026-W17",
            "date": "2026-04-29",
        },
        {
            "meter_id": "M1",
            "week": "2026-W16",
            "created_at": "2026-04-20T01:00:00+00:00",
        },
    ]

    rows = history_service.get_meter_history(
        "M1",
        "U1",
        period_days=7,
        now=datetime(2026, 5, 4, tzinfo=timezone.utc),
    )

    assert [row["week"] for row in rows] == ["2026-W18", "2026-W17"]


@patch("app.services.history_service.repositories")
def test_meter_history_caps_dense_history_and_keeps_order(mock_repo):
    mock_repo.get_readings_by_meter.return_value = [
        {
            "meter_id": "M1",
            "week": f"2026-W{i:02d}",
            "created_at": f"2026-05-{min(i, 28):02d}T01:00:00+00:00",
        }
        for i in range(20, 0, -1)
    ]

    rows = history_service.get_meter_history(
        "M1",
        "U1",
        period_days=30,
        now=datetime(2026, 5, 28, tzinfo=timezone.utc),
    )

    assert len(rows) == 12
    assert rows[0]["week"] == "2026-W20"
    assert rows[-1]["week"] == "2026-W09"
