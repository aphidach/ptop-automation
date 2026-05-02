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

WIDTH = 910
HEIGHT = 628
BG_COLOR = "#FFFFFF"
HEADER_FG = "#000000"
TOTAL_BG = "#FFD966"
BORDER_COLOR = "#000000"
TITLE_COLOR = "#000000"
SUBTITLE_COLOR = "#000000"
TOTAL_LABEL_COLOR = "#000000"
TITLE = "ข้อมูลการผลิตไฟฟ้า Solar Cells On-Grid โรงซ่อม 2 (ชุดที่ 1-4) และช่างยาง (ชุดที่ 5-8)"
AMOUNT_COLORS = [
    "#DDE3EA",
    "#C6E0B4",
    "#BDD7EE",
    "#8EAADB",
    "#FCE4D6",
    "#F8CBAD",
    "#F4B183",
    "#C65911",
]

FONT_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
    "/System/Library/Fonts/Supplemental/Thonburi.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]

FONT_BOLD_CANDIDATES = [
    "/System/Library/Fonts/Supplemental/Thonburi Bold.ttf",
    "/System/Library/Fonts/Supplemental/Arial Unicode Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]


@dataclass
class ReportReading:
    meter_id: str
    name: str
    sort_order: int
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


def _load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    paths = FONT_BOLD_CANDIDATES + FONT_CANDIDATES if bold else FONT_CANDIDATES
    for path in paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    logger.warning("No TTF font found, using Pillow default")
    return ImageFont.load_default()


def _fmt(value: Decimal) -> str:
    """Format Decimal without thousands separators, 1 decimal when fractional."""
    if value == value.to_integral_value():
        return str(int(value))
    return f"{value:.1f}"


def _fmt_baht(value: Decimal) -> str:
    """Format baht without thousands separators, matching the report image."""
    return _fmt(value)


def _format_thai_date(date_str: str) -> str:
    """Convert ISO date (YYYY-MM-DD) to Thai Buddhist date format."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        months = [
            "มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
            "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม",
        ]
        return f"วันที่ .....{dt.day}.. /......{months[dt.month - 1]}....../.....{dt.year + 543}....."
    except Exception:
        return date_str

def _to_sort_order(value: object, fallback: int) -> int:
    try:
        return int(str(value))
    except (TypeError, ValueError):
        return fallback

def _draw_centered_lines(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    box: tuple[int, int, int, int],
    font: ImageFont.ImageFont,
    fill: str,
    line_gap: int = 8,
) -> None:
    left, top, right, bottom = box
    heights = []
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        heights.append(bbox[3] - bbox[1])
    total_height = sum(heights) + line_gap * (len(lines) - 1)
    y = top + ((bottom - top) - total_height) / 2
    x = left + (right - left) / 2
    for line, height in zip(lines, heights):
        draw.text((x, y + height / 2), line, fill=fill, font=font, anchor="mm")
        y += height + line_gap

def _draw_grid(
    draw: ImageDraw.ImageDraw,
    x_positions: list[int],
    top: int,
    bottom: int,
    y_positions: list[int],
) -> None:
    for x in x_positions:
        draw.line([(x, top), (x, bottom)], fill=BORDER_COLOR, width=1)
    for y in y_positions:
        draw.line([(x_positions[0], y), (x_positions[-1], y)], fill=BORDER_COLOR, width=1)


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
    for index, r in enumerate(rows):
        meter_id = r.get("meter_id", "")
        meter = repositories.get_meter_by_id(meter_id)
        name = meter.get("name", meter_id) if meter else meter_id
        sort_order = _to_sort_order(meter.get("sort_order") if meter else None, index + 1)
        readings.append(ReportReading(
            meter_id=meter_id,
            name=name,
            sort_order=sort_order,
            current_value=Decimal(str(r.get("current_value", 0))),
            last_value=Decimal(str(r.get("last_value", 0))),
            produced_unit=Decimal(str(r.get("produced_unit", 0))),
            rate=Decimal(str(r.get("rate", 0))),
            amount=Decimal(str(r.get("amount", 0))),
        ))

    readings.sort(key=lambda rd: (rd.sort_order, rd.meter_id))

    total_unit = sum(rd.produced_unit for rd in readings)
    total_amount = sum(rd.amount for rd in readings)

    return ReportData(
        title=TITLE,
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

    font_title = _load_font(19, bold=True)
    font_date = _load_font(18)
    font_header = _load_font(18)
    font_cell = _load_font(18)
    font_total = _load_font(18)
    font_total_value = _load_font(18, bold=True)

    draw.text((WIDTH // 2, 8), data.title, fill=TITLE_COLOR, font=font_title, anchor="mt")
    draw.text((24, 54), data.date, fill=SUBTITLE_COLOR, font=font_date, anchor="la")

    table_left = 24
    table_top = 87
    header_height = 81
    row_height = 42
    col_widths = [134, 149, 159, 144, 141, 144]
    x_positions = [table_left]
    for width in col_widths:
        x_positions.append(x_positions[-1] + width)
    table_right = x_positions[-1]
    table_bottom = table_top + header_height + row_height * len(data.readings)

    headers = [
        ["ชุดที่", "(กำลังไฟฟ้า)"],
        ["อ่านครั้งหลัง", "(kWh)"],
        ["อ่านครั้งก่อน", "(kWh)"],
        ["ผลิตได้", "(kWh)"],
        ["อัตรา/หน่วย", "(บาท)"],
        ["คิดเป็นเงิน", "(บาท)"],
    ]

    draw.rectangle([table_left, table_top, table_right, table_bottom], fill=BG_COLOR)
    for idx, lines in enumerate(headers):
        _draw_centered_lines(
            draw,
            lines,
            (x_positions[idx], table_top, x_positions[idx + 1], table_top + header_height),
            font_header,
            HEADER_FG,
        )

    for i, rd in enumerate(data.readings):
        row_top = table_top + header_height + row_height * i
        row_bottom = row_top + row_height
        draw.rectangle(
            [x_positions[-2], row_top, table_right, row_bottom],
            fill=AMOUNT_COLORS[i % len(AMOUNT_COLORS)],
        )
        values = [
            f"{i + 1}. ({rd.name})",
            _fmt(rd.current_value),
            _fmt(rd.last_value),
            _fmt(rd.produced_unit),
            _fmt_baht(rd.rate),
            _fmt_baht(rd.amount),
        ]
        for col_idx, value in enumerate(values):
            _draw_centered_lines(
                draw,
                [value],
                (x_positions[col_idx], row_top, x_positions[col_idx + 1], row_bottom),
                font_cell,
                "#000000",
                line_gap=0,
            )

    y_positions = [table_top, table_top + header_height]
    y_positions.extend(
        table_top + header_height + row_height * i
        for i in range(1, len(data.readings) + 1)
    )
    _draw_grid(draw, x_positions, table_top, table_bottom, y_positions)

    total_top = 539
    total_bottom = 582
    total_left = 546
    total_mid = 721
    total_right = 895
    draw.rectangle([total_left, total_top, total_mid, total_bottom], fill=BG_COLOR, outline=BORDER_COLOR)
    draw.rectangle([total_mid, total_top, total_right, total_bottom], fill=TOTAL_BG, outline=BORDER_COLOR)
    _draw_centered_lines(
        draw,
        ["รวมเป็นเงิน (บาท)"],
        (total_left, total_top, total_mid, total_bottom),
        font_total,
        TOTAL_LABEL_COLOR,
        line_gap=0,
    )
    _draw_centered_lines(
        draw,
        [_fmt_baht(data.total_amount)],
        (total_mid, total_top, total_right, total_bottom),
        font_total_value,
        TOTAL_LABEL_COLOR,
        line_gap=0,
    )

    img.save(str(output_path))
    logger.info("Report image saved: %s", output_path)
    return str(output_path)
