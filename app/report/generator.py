from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from app.config import settings
from app.sheets import repositories

logger = logging.getLogger(__name__)

WIDTH = 1200
HEIGHT = 1600
BG_COLOR = "#FFFFFF"
HEADER_BG = "#C0C0C0"
HEADER_FG = "#000000"
ROW_EVEN = "#FFFFFF"
ROW_ODD = "#F5F5F5"
TOTAL_BG = "#FFEB3B"
BORDER_COLOR = "#000000"
TITLE_COLOR = "#000000"
SUBTITLE_COLOR = "#000000"
TOTAL_LABEL_COLOR = "#000000"

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Thonburi.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]


@dataclass
class ReportReading:
    meter_id: str
    name: str
    current_value: Decimal
    last_value: Decimal
    produced_unit: Decimal
    rate: Decimal
    amount: Decimal


@dataclass
class ReportData:
    title: str
    week: str
    date: str
    readings: list[ReportReading]
    total_produced_unit: Decimal
    total_amount: Decimal


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    logger.warning("No TTF font found, using Pillow default")
    return ImageFont.load_default()


def _fmt(value: Decimal) -> str:
    """Format Decimal with comma separator, 1 decimal when fractional."""
    if value == value.to_integral_value():
        return f"{int(value):,}"
    return f"{value:,.1f}"


def _fmt_baht(value: Decimal) -> str:
    """Format Decimal as baht, 1 decimal when fractional."""
    if value == value.to_integral_value():
        return f"{int(value):,}"
    return f"{value:,.1f}"


def _format_thai_date(date_str: str) -> str:
    """Convert ISO date (YYYY-MM-DD) to Thai Buddhist date format."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        months = [
            "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
            "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
        ]
        return f"วันที่ {dt.day} เดือน {months[dt.month - 1]}/{dt.year + 543}"
    except Exception:
        return date_str


def build_report_data(batch_id: str) -> ReportData | None:
    batch = repositories.get_batch_by_id(batch_id)
    if not batch:
        logger.warning("Batch '%s' not found", batch_id)
        return None

    rows = repositories.get_readings_by_batch(batch_id)
    if not rows:
        logger.warning("No readings for batch '%s'", batch_id)
        return None

    readings: list[ReportReading] = []
    for r in rows:
        meter_id = r.get("meter_id", "")
        meter = repositories.get_meter_by_id(meter_id)
        name = meter.get("name", meter_id) if meter else meter_id
        readings.append(ReportReading(
            meter_id=meter_id,
            name=name,
            current_value=Decimal(str(r.get("current_value", 0))),
            last_value=Decimal(str(r.get("last_value", 0))),
            produced_unit=Decimal(str(r.get("produced_unit", 0))),
            rate=Decimal(str(r.get("rate", 0))),
            amount=Decimal(str(r.get("amount", 0))),
        ))

    readings.sort(key=lambda rd: rd.meter_id)

    total_unit = sum(rd.produced_unit for rd in readings)
    total_amount = sum(rd.amount for rd in readings)

    return ReportData(
        title="ข้อมูลการผลิตไฟฟ้า Solar Cells On-Grid",
        week=batch.get("week", ""),
        date=_format_thai_date(batch.get("date", "")),
        readings=readings,
        total_produced_unit=total_unit,
        total_amount=total_amount,
    )


def generate_report_image(batch_id: str) -> str | None:
    data = build_report_data(batch_id)
    if data is None:
        return None

    report_dir = Path(settings.REPORT_DIR)
    report_dir.mkdir(parents=True, exist_ok=True)
    output_path = report_dir / f"{batch_id}.png"

    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_title = _load_font(48)
    font_subtitle = _load_font(28)
    font_header = _load_font(22)
    font_cell = _load_font(20)
    font_total = _load_font(24)

    y = 40

    # Title
    draw.text((WIDTH // 2, y), data.title, fill=TITLE_COLOR, font=font_title, anchor="mt")
    y += 70

    # Date line
    draw.text((WIDTH // 2, y), data.date, fill=SUBTITLE_COLOR, font=font_subtitle, anchor="mt")
    y += 60

    # Table
    cols = [
        ("จุดที่(กำลังไฟฟ้า)", 50),
        ("อ่านครั้งหลัง(kWh)", 230),
        ("อ่านครั้งก่อน(kWh)", 430),
        ("ผลต่างได้(kWh)", 620),
        ("อัตราหน่วย(บาท)", 790),
        ("คิดเป็นเงิน(บาท)", 960),
    ]
    col_x = [cx for _, cx in cols]
    table_left = 40
    table_right = WIDTH - 40
    row_height = 50

    # Header row
    draw.rectangle(
        [table_left, y, table_right, y + row_height],
        fill=HEADER_BG,
        outline=BORDER_COLOR,
    )
    for label, cx in cols:
        draw.text((table_left + cx, y + row_height // 2), label, fill=HEADER_FG, font=font_header, anchor="lm")
    y += row_height

    # Data rows
    for i, rd in enumerate(data.readings):
        bg = ROW_EVEN if i % 2 == 0 else ROW_ODD
        draw.rectangle(
            [table_left, y, table_right, y + row_height],
            fill=bg,
            outline=BORDER_COLOR,
        )
        values = [
            f"{i + 1}.({rd.name})",
            _fmt(rd.current_value),
            _fmt(rd.last_value),
            _fmt(rd.produced_unit),
            _fmt_baht(rd.rate),
            _fmt_baht(rd.amount),
        ]
        for val, cx in zip(values, col_x):
            draw.text((table_left + cx, y + row_height // 2), val, fill="#212121", font=font_cell, anchor="lm")
        y += row_height

    # Total row
    draw.rectangle(
        [table_left, y, table_right, y + row_height + 8],
        fill=TOTAL_BG,
        outline=BORDER_COLOR,
    )
    draw.text((table_left + 50, y + (row_height + 8) // 2), "รวมเป็นเงิน (บาท)", fill=TOTAL_LABEL_COLOR, font=font_total, anchor="lm")
    draw.text((table_left + 960, y + (row_height + 8) // 2), _fmt_baht(data.total_amount), fill=TOTAL_LABEL_COLOR, font=font_total, anchor="lm")
    y += row_height + 8

    img.save(str(output_path))
    logger.info("Report image saved: %s", output_path)
    return str(output_path)
