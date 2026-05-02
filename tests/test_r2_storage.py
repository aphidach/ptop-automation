from unittest.mock import patch

from app.storage.r2 import _build_endpoint_url, _build_public_url


def test_build_endpoint_url_strips_bucket_path():
    with patch("app.storage.r2.settings") as mock_settings:
        mock_settings.R2_ENDPOINT = "https://abc.r2.cloudflarestorage.com/my-bucket"

        endpoint = _build_endpoint_url()

    assert endpoint == "https://abc.r2.cloudflarestorage.com"


def test_build_public_url_uses_reports_key():
    with patch("app.storage.r2.settings") as mock_settings:
        mock_settings.R2_PUBLIC_URL = "https://cdn.example.com/"

        url = _build_public_url("reports/report.png")

    assert url == "https://cdn.example.com/reports/report.png"
