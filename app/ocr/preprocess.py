from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter, ImageOps


@dataclass
class PreprocessResult:
    original_path: Path
    ocr_image_path: Path
    crop_path: Path | None
    used_crop: bool
    success: bool
    crop_box: tuple[int, int, int, int] | None
    crop_size: tuple[int, int] | None
    reason: str


def prepare_meter_display_image(
    image_path: str | Path,
    output_dir: str | Path = "tmp/ocr-debug",
) -> PreprocessResult:
    original_path = Path(image_path)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        image = Image.open(original_path).convert("RGB")
    except Exception as exc:
        return PreprocessResult(
            original_path=original_path,
            ocr_image_path=original_path,
            crop_path=None,
            used_crop=False,
            success=False,
            crop_box=None,
            crop_size=None,
            reason=f"preprocess_open_failed:{exc}",
        )

    box = _detect_dark_display_region(image)
    if box is None:
        return PreprocessResult(
            original_path=original_path,
            ocr_image_path=original_path,
            crop_path=None,
            used_crop=False,
            success=False,
            crop_box=None,
            crop_size=None,
            reason="display_region_not_found",
        )

    crop = image.crop(box)
    crop = _enhance_crop(crop)
    crop_path = output_path / f"{original_path.stem}-display{original_path.suffix.lower() or '.jpg'}"
    crop.save(crop_path, quality=92)

    return PreprocessResult(
        original_path=original_path,
        ocr_image_path=crop_path,
        crop_path=crop_path,
        used_crop=True,
        success=True,
        crop_box=box,
        crop_size=crop.size,
        reason="display_region_crop",
    )


def _detect_dark_display_region(image: Image.Image) -> tuple[int, int, int, int] | None:
    width, height = image.size
    scale = min(1.0, 360 / max(width, height))
    small_size = (max(1, int(width * scale)), max(1, int(height * scale)))
    small = image.resize(small_size)
    gray = ImageOps.grayscale(small).filter(ImageFilter.MedianFilter(size=3))

    threshold = 115
    min_y = int(small_size[1] * 0.25)
    mask = gray.point(lambda value: 255 if value < threshold else 0)
    components = _connected_components(mask, min_y=min_y)
    if not components:
        return None

    best = max(components, key=_component_score)
    left, top, right, bottom, area = best
    comp_width = right - left + 1
    comp_height = bottom - top + 1
    image_area = small_size[0] * small_size[1]
    aspect = comp_width / comp_height if comp_height else 0

    if area < image_area * 0.015 or not 0.45 <= aspect <= 2.2:
        return None

    inv_scale = 1 / scale
    pad_x = int(comp_width * inv_scale * 0.08)
    pad_y = int(comp_height * inv_scale * 0.08)
    box = (
        max(0, int(left * inv_scale) - pad_x),
        max(0, int(top * inv_scale) - pad_y),
        min(width, int((right + 1) * inv_scale) + pad_x),
        min(height, int((bottom + 1) * inv_scale) + pad_y),
    )

    if (box[2] - box[0]) < width * 0.15 or (box[3] - box[1]) < height * 0.12:
        return None
    return box


def _connected_components(
    mask: Image.Image,
    *,
    min_y: int,
) -> list[tuple[int, int, int, int, int]]:
    width, height = mask.size
    pixels = mask.load()
    seen: set[tuple[int, int]] = set()
    components: list[tuple[int, int, int, int, int]] = []

    for y in range(min_y, height):
        for x in range(width):
            if pixels[x, y] == 0 or (x, y) in seen:
                continue

            stack = [(x, y)]
            seen.add((x, y))
            left = right = x
            top = bottom = y
            area = 0

            while stack:
                cx, cy = stack.pop()
                area += 1
                left = min(left, cx)
                right = max(right, cx)
                top = min(top, cy)
                bottom = max(bottom, cy)

                for nx, ny in (
                    (cx - 1, cy),
                    (cx + 1, cy),
                    (cx, cy - 1),
                    (cx, cy + 1),
                ):
                    if nx < 0 or nx >= width or ny < min_y or ny >= height:
                        continue
                    if (nx, ny) in seen or pixels[nx, ny] == 0:
                        continue
                    seen.add((nx, ny))
                    stack.append((nx, ny))

            components.append((left, top, right, bottom, area))

    return components


def _component_score(component: tuple[int, int, int, int, int]) -> float:
    left, top, right, bottom, area = component
    width = right - left + 1
    height = bottom - top + 1
    fill = area / (width * height)
    return area * (0.5 + fill)


def _enhance_crop(crop: Image.Image) -> Image.Image:
    max_side = max(crop.size)
    if max_side < 1200:
        scale = 1200 / max_side
        crop = crop.resize(
            (int(crop.width * scale), int(crop.height * scale)),
            Image.Resampling.LANCZOS,
        )
    crop = ImageOps.autocontrast(crop, cutoff=1)
    crop = ImageEnhance.Contrast(crop).enhance(1.35)
    crop = ImageEnhance.Sharpness(crop).enhance(1.2)
    return crop
