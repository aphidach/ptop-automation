from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageOps

from app.line.parser import (
    POSTBACK_HELP,
    POSTBACK_HISTORY,
    POSTBACK_LATEST_REPORT,
    POSTBACK_SETTINGS,
    POSTBACK_START_COLLECTION,
    POSTBACK_WEEKLY_SUMMARY,
)

RICHMENU_WIDTH = 2500
RICHMENU_HEIGHT = 1686
RICHMENU_DIR = Path(__file__).resolve().parents[2] / "Richmenu image"
RICHMENU_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "tmp" / "richmenu"
RICHMENU_IMAGE_NAME = "richmenu-v2-line.png"
RICHMENU_SPEC_NAME = "richmenu-v2-line.json"
RICHMENU_MAX_IMAGE_BYTES = 1_000_000
_PNG_COLOR_ATTEMPTS = (256, 128, 64, 32)


@dataclass(frozen=True)
class RichMenuButtonSpec:
    name: str
    action: str
    image_file: str
    label: str


def _default_buttons() -> list[RichMenuButtonSpec]:
    return [
        RichMenuButtonSpec(
            name="start_collection",
            action=POSTBACK_START_COLLECTION,
            image_file="richmenu-start-collection.png",
            label="บันทึกมิเตอร์",
        ),
        RichMenuButtonSpec(
            name="weekly_summary",
            action=POSTBACK_WEEKLY_SUMMARY,
            image_file="richmenu-weekly-summary.png",
            label="สรุปสัปดาห์",
        ),
        RichMenuButtonSpec(
            name="latest_report",
            action=POSTBACK_LATEST_REPORT,
            image_file="richmenu-latest-report.png",
            label="รายงานล่าสุด",
        ),
        RichMenuButtonSpec(
            name="history",
            action=POSTBACK_HISTORY,
            image_file="richmenu-history.png",
            label="ประวัติ",
        ),
        RichMenuButtonSpec(
            name="settings",
            action=POSTBACK_SETTINGS,
            image_file="richmenu-settings.png",
            label="ตั้งค่า",
        ),
        RichMenuButtonSpec(
            name="help",
            action=POSTBACK_HELP,
            image_file="richmenu-help.png",
            label="Help",
        ),
    ]


def _load_image(path: Path) -> Image.Image:
    with Image.open(path) as image:
        return image.convert("RGBA")


def _build_spec(
    buttons: list[RichMenuButtonSpec],
    widths: tuple[int, int, int],
    heights: tuple[int, int],
) -> dict:
    areas = []
    for index, button in enumerate(buttons):
        x = 0
        for i in range(index % 3):
            x += widths[i]
        y = 0 if index < 3 else heights[0]
        area = {
            "bounds": {
                "x": x,
                "y": y,
                "width": widths[index % 3],
                "height": heights[index // 3],
            },
            "action": {
                "type": "postback",
                "data": f"action={button.action}",
                "displayText": button.label,
            },
        }
        areas.append(area)

    return {
        "size": {"width": RICHMENU_WIDTH, "height": RICHMENU_HEIGHT},
        "selected": False,
        "name": "ptop-automation-v2-main",
        "chatBarText": "เมนูหลัก",
        "areas": areas,
    }


def _save_line_compatible_image(canvas: Image.Image, image_path: Path) -> Path:
    rgb = canvas.convert("RGB")
    for colors in _PNG_COLOR_ATTEMPTS:
        quantized = rgb.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
        quantized.save(str(image_path), format="PNG", optimize=True, compress_level=9)
        if image_path.stat().st_size <= RICHMENU_MAX_IMAGE_BYTES:
            return image_path

    jpeg_path = image_path.with_suffix(".jpg")
    for quality in (92, 88, 84, 80, 76, 72):
        rgb.save(
            str(jpeg_path),
            format="JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
        )
        if jpeg_path.stat().st_size <= RICHMENU_MAX_IMAGE_BYTES:
            return jpeg_path

    raise ValueError("Rich menu image exceeds LINE 1 MB upload limit")


def compose_richmenu_image(
    output_dir: str | Path | None = None,
    source_dir: str | Path | None = None,
    buttons: list[RichMenuButtonSpec] | None = None,
) -> tuple[Path, Path]:
    output_directory = Path(output_dir or RICHMENU_OUTPUT_DIR)
    source_directory = Path(source_dir or RICHMENU_DIR)
    button_specs = buttons or _default_buttons()
    if len(button_specs) != 6:
        raise ValueError("Expected exactly 6 rich menu buttons")

    # LINE-compatible fixed-size canvas for 3x2 layout.
    canvas = Image.new("RGBA", (RICHMENU_WIDTH, RICHMENU_HEIGHT), (0, 0, 0, 255))
    widths = (834, 833, 833)
    heights = (843, 843)

    for index, spec in enumerate(button_specs):
        x = 0
        for i in range(index % 3):
            x += widths[i]
        y = 0 if index < 3 else heights[0]
        width = widths[index % 3]
        height = heights[index // 3]

        source_path = source_directory / spec.image_file
        if source_path.exists():
            source = _load_image(source_path)
            resized = ImageOps.fit(source, (width, height), method=Image.Resampling.LANCZOS)
        else:
            fallback = Image.new("RGB", (width, height), (16, 16, 16))
            resized = fallback

        canvas.paste(resized, (x, y))

    output_directory.mkdir(parents=True, exist_ok=True)
    image_path = output_directory / RICHMENU_IMAGE_NAME
    spec_path = output_directory / RICHMENU_SPEC_NAME
    spec = _build_spec(button_specs, widths, heights)

    image_path = _save_line_compatible_image(canvas, image_path)
    with spec_path.open("w", encoding="utf-8") as fp:
        json.dump(spec, fp, ensure_ascii=False, indent=2)
        fp.write("\n")

    return image_path, spec_path
