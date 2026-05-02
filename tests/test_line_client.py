from app.line.client import _is_https_url


def test_is_https_url_accepts_https_url():
    assert _is_https_url("https://example.com/reports/a.png") is True


def test_is_https_url_rejects_http_url():
    assert _is_https_url("http://example.com/reports/a.png") is False


def test_is_https_url_rejects_local_path():
    assert _is_https_url("reports/a.png") is False
