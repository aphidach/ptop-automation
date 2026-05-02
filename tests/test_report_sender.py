from unittest.mock import AsyncMock, patch

import pytest

from app.report.sender import _build_report_url, send_report, send_report_if_complete


def test_build_report_url_uses_app_base_url():
    with patch("app.report.sender.settings") as mock_settings:
        mock_settings.APP_BASE_URL = "https://example.com/"
        url = _build_report_url("2026-W19-U1.png")

    assert url == "https://example.com/reports/2026-W19-U1.png"


@pytest.mark.anyio
async def test_send_report_skips_image_push_when_base_url_is_not_https():
    with patch("app.report.sender.settings") as mock_settings, \
         patch("app.report.sender.repositories") as mock_repositories, \
         patch("app.report.sender.generate_report_image") as mock_generate, \
         patch("app.report.sender.push_image", new_callable=AsyncMock) as mock_push_image, \
         patch("app.report.sender.push_text", new_callable=AsyncMock) as mock_push_text:
        mock_settings.APP_BASE_URL = "http://localhost:8000"
        mock_repositories.get_batch_by_id.return_value = {"status": "complete"}
        mock_generate.return_value = "reports/2026-W19-U1.png"

        await send_report_if_complete("2026-W19-U1", "U1")

    mock_push_image.assert_not_called()
    mock_repositories.update_batch_status.assert_not_called()
    mock_push_text.assert_called_once()
    assert "APP_BASE_URL" in mock_push_text.call_args.args[1]
    assert "http://localhost:8000/reports/2026-W19-U1.png" in mock_push_text.call_args.args[1]


@pytest.mark.anyio
async def test_send_report_does_not_mark_reported_when_image_push_fails():
    with patch("app.report.sender.settings") as mock_settings, \
         patch("app.report.sender.repositories") as mock_repositories, \
         patch("app.report.sender.generate_report_image") as mock_generate, \
         patch("app.report.sender.push_image", new_callable=AsyncMock) as mock_push_image, \
         patch("app.report.sender.push_text", new_callable=AsyncMock) as mock_push_text:
        mock_settings.APP_BASE_URL = "https://example.com"
        mock_repositories.get_batch_by_id.return_value = {"status": "complete"}
        mock_generate.return_value = "reports/2026-W19-U1.png"
        mock_push_image.return_value = False

        await send_report_if_complete("2026-W19-U1", "U1")

    mock_push_image.assert_called_once_with(
        "U1",
        "https://example.com/reports/2026-W19-U1.png",
        "https://example.com/reports/2026-W19-U1.png",
    )
    mock_repositories.update_batch_status.assert_not_called()
    mock_push_text.assert_called_once()
    assert "REPORT" in mock_push_text.call_args.args[1]
    assert "https://example.com/reports/2026-W19-U1.png" in mock_push_text.call_args.args[1]


@pytest.mark.anyio
async def test_send_report_marks_reported_after_successful_image_push():
    with patch("app.report.sender.settings") as mock_settings, \
         patch("app.report.sender.repositories") as mock_repositories, \
         patch("app.report.sender.generate_report_image") as mock_generate, \
         patch("app.report.sender.push_image", new_callable=AsyncMock) as mock_push_image, \
         patch("app.report.sender.push_text", new_callable=AsyncMock):
        mock_settings.APP_BASE_URL = "https://example.com"
        mock_repositories.get_batch_by_id.return_value = {"status": "complete"}
        mock_generate.return_value = "reports/2026-W19-U1.png"
        mock_push_image.return_value = True

        await send_report_if_complete("2026-W19-U1", "U1")

    mock_repositories.update_batch_status.assert_called_once_with("2026-W19-U1", "reported")


@pytest.mark.anyio
async def test_manual_send_report_does_not_mark_reported():
    with patch("app.report.sender.settings") as mock_settings, \
         patch("app.report.sender.repositories") as mock_repositories, \
         patch("app.report.sender.generate_report_image") as mock_generate, \
         patch("app.report.sender.push_image", new_callable=AsyncMock) as mock_push_image, \
         patch("app.report.sender.push_text", new_callable=AsyncMock):
        mock_settings.APP_BASE_URL = "https://example.com"
        mock_generate.return_value = "reports/2026-W19-U1.png"
        mock_push_image.return_value = True

        sent = await send_report("2026-W19-U1", "U1")

    assert sent is True
    mock_repositories.update_batch_status.assert_not_called()
