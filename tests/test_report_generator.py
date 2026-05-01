"""Tests for app.report.generator using mock data (no Google Sheets required)."""
from __future__ import annotations

import os
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from app.report.generator import (
    ReportData,
    ReportReading,
    _fmt,
    _fmt_baht,
    generate_report_image,
)


def test_fmt():
    assert _fmt(Decimal(12500)) == "12,500"
    assert _fmt(Decimal(0)) == "0"


def test_fmt_baht():
    assert _fmt_baht(Decimal("2100.00")) == "2,100.00"
    assert _fmt_baht(Decimal("2133.60")) == "2,133.60"


def _mock_report_data():
    return ReportData(
        title="Solar Weekly Report",
        week="2026-W19",
        date="2026-05-04",
        readings=[
            ReportReading("M1", "Solar 1", Decimal(12500), Decimal(12000), Decimal(500), Decimal("4.2"), Decimal(2100)),
            ReportReading("M2", "Solar 2", Decimal(9800), Decimal(9500), Decimal(300), Decimal("4.2"), Decimal(1260)),
            ReportReading("M3", "Solar 3", Decimal(15200), Decimal(14800), Decimal(400), Decimal("4.2"), Decimal(1680)),
        ],
        total_produced_unit=Decimal(1200),
        total_amount=Decimal(5040),
    )


@patch("app.report.generator.build_report_data")
def test_generate_report_image(mock_build):
    mock_build.return_value = _mock_report_data()
    output_dir = "tmp/test_reports"
    with patch("app.report.generator.settings") as mock_settings:
        mock_settings.REPORT_DIR = output_dir
        result = generate_report_image("2026-W19-Utest")

    assert result is not None
    path = Path(result)
    assert path.exists()
    assert path.suffix == ".png"
    assert path.name == "2026-W19-Utest.png"

    # Verify image dimensions
    from PIL import Image

    img = Image.open(str(path))
    assert img.width == 1200
    assert img.height == 1600

    # Cleanup
    path.unlink()
    Path(output_dir).rmdir()


@patch("app.report.generator.build_report_data")
def test_generate_report_returns_none_when_no_data(mock_build):
    mock_build.return_value = None
    result = generate_report_image("nonexistent-batch")
    assert result is None
