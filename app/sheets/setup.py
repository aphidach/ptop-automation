"""Initialize Google Sheets tabs with headers.

Usage:
    python -m app.sheets.setup
"""

import logging

from app.sheets.client import sheets_client

logging.basicConfig(level=logging.INFO)


def main():
    sheets_client.setup_tabs()
    print("Spreadsheet tabs initialized successfully.")

    meters = sheets_client.get_active_meters()
    print(f"Active meters: {len(meters)}")
    for m in meters:
        print(f"  {m.get('meter_id')}: {m.get('name')}")


if __name__ == "__main__":
    main()
