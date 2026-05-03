from __future__ import annotations

import os
from urllib.parse import urlparse

LINE_CARD_START_COLLECTION_HERO_ASSET = "solar-meter-mascot-hero-v0.2.0.png"


def _is_https_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _line_card_asset_url(asset_name: str, direct_env: str | None = None) -> str | None:
    if direct_env:
        direct_url = os.getenv(direct_env, "").strip()
        if direct_url:
            return direct_url if _is_https_url(direct_url) else None

    base_url = os.getenv("LINE_CARD_IMAGE_BASE_URL", "").strip().rstrip("/")
    if _is_https_url(base_url):
        return f"{base_url}/{asset_name}"
    return None


def _start_collection_hero_url() -> str | None:
    return _line_card_asset_url(
        LINE_CARD_START_COLLECTION_HERO_ASSET,
        "LINE_CARD_START_COLLECTION_HERO_URL",
    )
