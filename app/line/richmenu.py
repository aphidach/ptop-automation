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
RICHMENU_HEIGHT = 1500
RICHMENU_DIR = Path(__file__).resolve().parents[1] / "assets" / "richmenu"
RICHMENU_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "tmp" / "richmenu"
RICHMENU_IMAGE_NAME = "richmenu-v2-line.png"
RICHMENU_SPEC_NAME = "richmenu-v2-line.json"
RICHMENU_MAX_IMAGE_BYTES = 1_000_000
_PNG_COLOR_ATTEMPTS = (256, 128, 64, 32)
_PANUAN_STYLE_BOUNDS = (
    {"x": 0, "y": 0, "width": 1503, "height": 1127},
    {"x": 1530, "y": 0, "width": 465, "height": 543},
    {"x": 2030, "y": 0, "width": 470, "height": 543},
    {"x": 1530, "y": 586, "width": 465, "height": 543},
    {"x": 2030, "y": 586, "width": 470, "height": 543},
    {"x": 0, "y": 1170, "width": 2500, "height": 330},
)


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
    bounds: tuple[dict[str, int], ...],
) -> dict:
    areas = []
    for button, area_bounds in zip(buttons, bounds):
        area = {
            "bounds": dict(area_bounds),
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

    # LINE-compatible fixed-size canvas matching the provided Panuan-style mock.
    canvas = Image.new("RGBA", (RICHMENU_WIDTH, RICHMENU_HEIGHT), (0, 0, 0, 255))
    bounds = _PANUAN_STYLE_BOUNDS

    for spec, area_bounds in zip(button_specs, bounds):
        x = area_bounds["x"]
        y = area_bounds["y"]
        width = area_bounds["width"]
        height = area_bounds["height"]

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
    spec = _build_spec(button_specs, bounds)

    image_path = _save_line_compatible_image(canvas, image_path)
    with spec_path.open("w", encoding="utf-8") as fp:
        json.dump(spec, fp, ensure_ascii=False, indent=2)
        fp.write("\n")

    return image_path, spec_path
