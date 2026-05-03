from unittest.mock import AsyncMock, patch

import pytest

from app.report.sender import (
    _build_report_delivery_url,
    _build_report_url,
    _cache_bust_report_url,
    send_report,
    send_report_if_complete,
)
from app.storage.r2 import R2ConfigError, R2UploadError


def test_build_report_url_uses_app_base_url():
    with patch("app.report.sender.settings") as mock_settings:
        mock_settings.APP_BASE_URL = "https://example.com/"
        url = _build_report_url("2026-W19-U1.png")

    assert url == "https://example.com/reports/2026-W19-U1.png"


def test_cache_bust_report_url_adds_stable_version_parameter():
    assert (
        _cache_bust_report_url("https://example.com/reports/2026-W19-U1.png", version=123)
        == "https://example.com/reports/2026-W19-U1.png?v=123"
    )
    assert (
        _cache_bust_report_url("https://example.com/reports/2026-W19-U1.png?x=1&v=old", version=123)
        == "https://example.com/reports/2026-W19-U1.png?x=1&v=123"
    )


def test_build_report_delivery_url_uploads_to_r2():
    with patch("app.report.sender.settings") as mock_settings, \
         patch("app.report.sender.upload_report_image") as mock_upload:
        mock_settings.REPORT_IMAGE_STORAGE = "r2"
        mock_upload.return_value = "https://cdn.example.com/reports/2026-W19-U1.png"

        url = _build_report_delivery_url("reports/2026-W19-U1.png")

    assert url == "https://cdn.example.com/reports/2026-W19-U1.png"
    mock_upload.assert_called_once_with("reports/2026-W19-U1.png")


@pytest.mark.anyio
async def test_send_report_skips_image_push_when_base_url_is_not_https():
    with patch("app.report.sender.settings") as mock_settings, \
         patch("app.report.sender.repositories") as mock_repositories, \
         patch("app.report.sender.generate_report_image") as mock_generate, \
         patch("app.report.sender.push_image", new_callable=AsyncMock) as mock_push_image, \
         patch("app.report.sender.push_text", new_callable=AsyncMock) as mock_push_text:
        mock_settings.APP_BASE_URL = "http://localhost:8000"
        mock_settings.REPORT_IMAGE_STORAGE = "local"
        mock_repositories.get_batch_by_id.return_value = {"status": "complete"}
        mock_generate.return_value = "reports/2026-W19-U1.png"

        await send_report_if_complete("2026-W19-U1", "U1")

    mock_push_image.assert_not_called()
    mock_repositories.update_batch_report_image_url.assert_not_called()
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
         patch("app.report.sender.push_text", new_callable=AsyncMock) as mock_push_text, \
         patch("app.report.sender.time.time_ns", return_value=123456789):
        mock_settings.APP_BASE_URL = "https://example.com"
        mock_settings.REPORT_IMAGE_STORAGE = "local"
        mock_repositories.get_batch_by_id.return_value = {"status": "complete"}
        mock_generate.return_value = "reports/2026-W19-U1.png"
        mock_push_image.return_value = False

        await send_report_if_complete("2026-W19-U1", "U1")

    mock_push_image.assert_called_once_with(
        "U1",
        "https://example.com/reports/2026-W19-U1.png?v=123456789",
        "https://example.com/reports/2026-W19-U1.png?v=123456789",
    )
    mock_repositories.update_batch_report_image_url.assert_called_once_with(
        "2026-W19-U1",
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
         patch("app.report.sender.push_text", new_callable=AsyncMock) as mock_push_text, \
         patch("app.report.sender.time.time_ns", return_value=123456789):
        mock_settings.APP_BASE_URL = "https://example.com"
        mock_settings.REPORT_IMAGE_STORAGE = "local"
        mock_repositories.get_batch_by_id.return_value = {"status": "complete"}
        mock_generate.return_value = "reports/2026-W19-U1.png"
        mock_push_image.return_value = True

        await send_report_if_complete("2026-W19-U1", "U1")

    mock_repositories.update_batch_report_image_url.assert_called_once_with(
        "2026-W19-U1",
        "https://example.com/reports/2026-W19-U1.png",
    )
    mock_push_image.assert_called_once_with(
        "U1",
        "https://example.com/reports/2026-W19-U1.png?v=123456789",
        "https://example.com/reports/2026-W19-U1.png?v=123456789",
    )
    mock_repositories.update_batch_status.assert_called_once_with("2026-W19-U1", "reported")
    mock_push_text.assert_not_called()


@pytest.mark.anyio
async def test_manual_send_report_does_not_mark_reported():
    with patch("app.report.sender.settings") as mock_settings, \
         patch("app.report.sender.repositories") as mock_repositories, \
         patch("app.report.sender.generate_report_image") as mock_generate, \
         patch("app.report.sender.push_image", new_callable=AsyncMock) as mock_push_image, \
         patch("app.report.sender.push_text", new_callable=AsyncMock) as mock_push_text, \
         patch("app.report.sender.time.time_ns", return_value=123456789):
        mock_settings.APP_BASE_URL = "https://example.com"
        mock_settings.REPORT_IMAGE_STORAGE = "local"
        mock_generate.return_value = "reports/2026-W19-U1.png"
        mock_push_image.return_value = True

        sent = await send_report("2026-W19-U1", "U1")

    assert sent is True
    mock_repositories.update_batch_report_image_url.assert_called_once_with(
        "2026-W19-U1",
        "https://example.com/reports/2026-W19-U1.png",
    )
    mock_push_image.assert_called_once_with(
        "U1",
        "https://example.com/reports/2026-W19-U1.png?v=123456789",
        "https://example.com/reports/2026-W19-U1.png?v=123456789",
    )
    mock_repositories.update_batch_status.assert_not_called()
    mock_push_text.assert_not_called()


@pytest.mark.anyio
async def test_send_report_uses_r2_url_and_marks_reported():
    with patch("app.report.sender.settings") as mock_settings, \
         patch("app.report.sender.repositories") as mock_repositories, \
         patch("app.report.sender.generate_report_image") as mock_generate, \
         patch("app.report.sender.upload_report_image") as mock_upload, \
         patch("app.report.sender.push_image", new_callable=AsyncMock) as mock_push_image, \
         patch("app.report.sender.push_text", new_callable=AsyncMock) as mock_push_text, \
         patch("app.report.sender.time.time_ns", return_value=123456789):
        mock_settings.REPORT_IMAGE_STORAGE = "r2"
        mock_repositories.get_batch_by_id.return_value = {"status": "complete"}
        mock_generate.return_value = "reports/2026-W19-U1.png"
        mock_upload.return_value = "https://cdn.example.com/reports/2026-W19-U1.png"
        mock_push_image.return_value = True

        await send_report_if_complete("2026-W19-U1", "U1")

    mock_push_image.assert_called_once_with(
        "U1",
        "https://cdn.example.com/reports/2026-W19-U1.png?v=123456789",
        "https://cdn.example.com/reports/2026-W19-U1.png?v=123456789",
    )
    mock_repositories.update_batch_report_image_url.assert_called_once_with(
        "2026-W19-U1",
        "https://cdn.example.com/reports/2026-W19-U1.png",
    )
    mock_repositories.update_batch_status.assert_called_once_with("2026-W19-U1", "reported")
    mock_push_text.assert_not_called()


@pytest.mark.anyio
async def test_send_report_does_not_push_when_r2_config_is_missing():
    with patch("app.report.sender.settings") as mock_settings, \
         patch("app.report.sender.repositories") as mock_repositories, \
         patch("app.report.sender.generate_report_image") as mock_generate, \
         patch("app.report.sender.upload_report_image") as mock_upload, \
         patch("app.report.sender.push_image", new_callable=AsyncMock) as mock_push_image, \
         patch("app.report.sender.push_text", new_callable=AsyncMock) as mock_push_text:
        mock_settings.REPORT_IMAGE_STORAGE = "r2"
        mock_repositories.get_batch_by_id.return_value = {"status": "complete"}
        mock_generate.return_value = "reports/2026-W19-U1.png"
        mock_upload.side_effect = R2ConfigError("Missing R2 config: R2_BUCKET")

        await send_report_if_complete("2026-W19-U1", "U1")

    mock_push_image.assert_not_called()
    mock_repositories.update_batch_report_image_url.assert_not_called()
    mock_repositories.update_batch_status.assert_not_called()
    mock_push_text.assert_called_once()
    assert "R2" in mock_push_text.call_args.args[1]


@pytest.mark.anyio
async def test_send_report_does_not_push_when_r2_upload_fails():
    with patch("app.report.sender.settings") as mock_settings, \
         patch("app.report.sender.repositories") as mock_repositories, \
         patch("app.report.sender.generate_report_image") as mock_generate, \
         patch("app.report.sender.upload_report_image") as mock_upload, \
         patch("app.report.sender.push_image", new_callable=AsyncMock) as mock_push_image, \
         patch("app.report.sender.push_text", new_callable=AsyncMock) as mock_push_text:
        mock_settings.REPORT_IMAGE_STORAGE = "r2"
        mock_repositories.get_batch_by_id.return_value = {"status": "complete"}
        mock_generate.return_value = "reports/2026-W19-U1.png"
        mock_upload.side_effect = R2UploadError("Failed to upload report image")

        await send_report_if_complete("2026-W19-U1", "U1")

    mock_push_image.assert_not_called()
    mock_repositories.update_batch_report_image_url.assert_not_called()
    mock_repositories.update_batch_status.assert_not_called()
    mock_push_text.assert_called_once()
    assert "R2" in mock_push_text.call_args.args[1]
