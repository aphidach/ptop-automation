import asyncio
import tomllib
from pathlib import Path

from fastapi.testclient import TestClient

import app.main as app_main
from app.config import settings
from app.main import app, health
from app.version import __version__


def test_app_version_is_current_release():
    assert __version__ == "0.3.0"


def test_package_version_matches_app_version():
    pyproject = tomllib.loads(Path("pyproject.toml").read_text())

    assert pyproject["project"]["version"] == __version__
    assert app.version == settings.APP_VERSION


def test_log_level_defaults_to_info():
    assert settings.LOG_LEVEL == "INFO"


def test_health_includes_release_version():
    assert asyncio.run(health()) == {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
    }


def test_storage_sync_health_endpoint_reports_counts():
    with TestClient(app) as client:
        response = client.get("/api/storage/sync/health")

    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["pending_count"] == 0
    assert body["failed_count"] == 0


def test_lifespan_does_not_run_sheets_sync_when_disabled(monkeypatch):
    calls = []
    monkeypatch.setattr(app_main.settings, "SHEETS_SYNC_ENABLED", False)
    monkeypatch.setattr(
        app_main.storage_sync,
        "pull_business_config_from_sheets",
        lambda: calls.append("pull") or True,
    )
    monkeypatch.setattr(
        app_main.storage_sync,
        "flush_outbox",
        lambda: calls.append("flush") or 0,
    )

    with TestClient(app_main.create_app()):
        pass

    assert calls == []


def test_lifespan_runs_sheets_sync_when_enabled(monkeypatch):
    calls = []
    monkeypatch.setattr(app_main.settings, "SHEETS_SYNC_ENABLED", True)
    monkeypatch.setattr(app_main.settings, "SHEETS_STARTUP_PULL_ENABLED", True)
    monkeypatch.setattr(
        app_main.storage_sync,
        "pull_business_config_from_sheets",
        lambda: calls.append("pull") or True,
    )
    monkeypatch.setattr(
        app_main.storage_sync,
        "flush_outbox",
        lambda: calls.append("flush") or 0,
    )

    async def fake_loop():
        calls.append("loop")
        await asyncio.sleep(3600)

    monkeypatch.setattr(app_main.storage_sync, "periodic_sync_loop", fake_loop)

    with TestClient(app_main.create_app()):
        pass

    assert calls == ["pull", "flush", "loop"]
