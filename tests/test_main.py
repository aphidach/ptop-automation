import asyncio
import tomllib
from pathlib import Path

from app.config import settings
from app.main import app, health
from app.version import __version__


def test_app_version_is_current_release():
    assert __version__ == "0.1.2"


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
