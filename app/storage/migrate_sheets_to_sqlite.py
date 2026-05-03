from __future__ import annotations

import logging

from app.storage.sync import pull_business_config_from_sheets
from app.storage.sqlite import sqlite_client

logging.basicConfig(level=logging.INFO)


def main() -> None:
    sqlite_client.setup()
    if not pull_business_config_from_sheets():
        raise SystemExit(1)
    print("Migrated business config from Google Sheets to SQLite.")


if __name__ == "__main__":
    main()
