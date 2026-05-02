from __future__ import annotations

import argparse
import asyncio
import csv
import json
import sys
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.config import settings
from app.ocr.confidence import score_ocr_reading
from app.ocr.rate_limiter import OcrRateLimiter
from app.ocr.paddle import PaddleOcrClient
from app.ocr.preprocess import PreprocessResult, prepare_meter_display_image
from app.ocr.value_parser import ParseResult, parse_meter_value

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
DEFAULT_IMAGE_DIR = Path("tmp/test-ocr")
DEFAULT_REPORT_DIR = Path("reports/ocr")
DEFAULT_DEBUG_DIR = Path("tmp/ocr-debug")
DEFAULT_TIMEZONE = "Asia/Bangkok"
PARSER_MODE = "field_aware_energy"
ENGINE_OPENTYPHOON = "opentyphoon"
ENGINE_PADDLE = "paddle"
ENGINE_ALL = "all"


@dataclass
class ExpectedReading:
    value: Decimal
    meter_id: str = ""


@dataclass
class EvaluationRow:
    engine: str
    image_path: Path
    ocr_image_path: Path
    expected: ExpectedReading | None
    raw_text: str
    parsed: ParseResult
    confidence_level: str
    confidence_reason: str
    confidence_warnings: list[str]
    preprocess: PreprocessResult | None
    duration_ms: int
    error: str | None

    @property
    def parsed_value(self) -> Decimal | None:
        return self.parsed.value

    @property
    def correct(self) -> bool | None:
        if self.expected is None or self.parsed_value is None:
            return None
        return self.parsed_value == self.expected.value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate OCR accuracy against real meter photos."
    )
    parser.add_argument(
        "--image-dir",
        type=Path,
        default=DEFAULT_IMAGE_DIR,
        help="Directory containing test images.",
    )
    parser.add_argument(
        "--labels",
        type=Path,
        default=None,
        help=(
            "Optional CSV/JSON labels file. Defaults to labels.csv, "
            "expected.csv, or labels.json inside --image-dir when present."
        ),
    )
    parser.add_argument(
        "--report-dir",
        type=Path,
        default=DEFAULT_REPORT_DIR,
        help="Directory for generated Markdown reports.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Maximum number of images to evaluate. 0 means all images.",
    )
    parser.add_argument(
        "--timezone",
        default=settings.TIMEZONE or DEFAULT_TIMEZONE,
        help="Timezone used in report timestamps.",
    )
    parser.add_argument(
        "--engine",
        default=ENGINE_OPENTYPHOON,
        help="OCR engine: opentyphoon, paddle, all, or a comma-separated list.",
    )
    parser.add_argument(
        "--preprocess",
        dest="preprocess",
        action="store_true",
        default=True,
        help="Crop/enhance the display region before OCR.",
    )
    parser.add_argument(
        "--no-preprocess",
        dest="preprocess",
        action="store_false",
        help="Skip display crop generation.",
    )
    parser.add_argument(
        "--use-crop-for-ocr",
        action="store_true",
        help="Send the generated display crop to OCR when preprocessing succeeds.",
    )
    parser.add_argument(
        "--debug-dir",
        type=Path,
        default=DEFAULT_DEBUG_DIR,
        help="Directory for OCR preprocessing debug crops.",
    )
    return parser.parse_args()


def find_images(image_dir: Path, limit: int = 0) -> list[Path]:
    if not image_dir.exists():
        raise FileNotFoundError(f"Image directory not found: {image_dir}")

    images = sorted(
        path
        for path in image_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    )
    if limit > 0:
        return images[:limit]
    return images


def resolve_labels_path(image_dir: Path, labels_path: Path | None) -> Path | None:
    if labels_path:
        return labels_path

    for filename in ("labels.csv", "expected.csv", "labels.json"):
        candidate = image_dir / filename
        if candidate.exists():
            return candidate
    return None


def load_labels(labels_path: Path | None) -> dict[str, ExpectedReading]:
    if labels_path is None:
        return {}
    if not labels_path.exists():
        raise FileNotFoundError(f"Labels file not found: {labels_path}")

    if labels_path.suffix.lower() == ".json":
        return load_json_labels(labels_path)
    return load_csv_labels(labels_path)


def load_csv_labels(labels_path: Path) -> dict[str, ExpectedReading]:
    labels: dict[str, ExpectedReading] = {}
    with labels_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            filename = first_present(row, "file", "filename", "image", "image_path")
            raw_value = first_present(row, "expected_value", "expected", "value")
            if not filename or not raw_value:
                continue
            labels[Path(filename).name] = ExpectedReading(
                value=parse_decimal(raw_value),
                meter_id=first_present(row, "meter_id", "meter") or "",
            )
    return labels


def load_json_labels(labels_path: Path) -> dict[str, ExpectedReading]:
    labels: dict[str, ExpectedReading] = {}
    with labels_path.open(encoding="utf-8") as f:
        data = json.load(f)

    items = data.items() if isinstance(data, dict) else enumerate(data)
    for key, value in items:
        if isinstance(value, dict):
            filename = first_present(value, "file", "filename", "image", "image_path")
            raw_value = first_present(value, "expected_value", "expected", "value")
            meter_id = first_present(value, "meter_id", "meter") or ""
            if not filename:
                filename = str(key)
        else:
            filename = str(key)
            raw_value = str(value)
            meter_id = ""
        if not filename or not raw_value:
            continue
        labels[Path(filename).name] = ExpectedReading(
            value=parse_decimal(raw_value),
            meter_id=meter_id,
        )
    return labels


def first_present(row: dict, *keys: str) -> str:
    for key in keys:
        value = row.get(key)
        if value is not None and str(value).strip():
            return str(value).strip()
    return ""


def parse_decimal(value: str) -> Decimal:
    cleaned = value.replace(",", "").strip()
    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"Invalid expected value: {value}") from exc


def parse_engines(value: str) -> list[str]:
    requested = [item.strip().lower() for item in value.split(",") if item.strip()]
    if not requested:
        return [ENGINE_OPENTYPHOON]
    if ENGINE_ALL in requested:
        return [ENGINE_OPENTYPHOON, ENGINE_PADDLE]

    supported = {ENGINE_OPENTYPHOON, ENGINE_PADDLE}
    unsupported = [engine for engine in requested if engine not in supported]
    if unsupported:
        raise ValueError(f"Unsupported OCR engine: {', '.join(unsupported)}")
    return requested


async def evaluate_images(
    images: list[Path],
    labels: dict[str, ExpectedReading],
    engines: list[str],
    preprocess_enabled: bool,
    use_crop_for_ocr: bool,
    debug_dir: Path,
) -> list[EvaluationRow]:
    rows: list[EvaluationRow] = []
    opentyphoon_limiter: OcrRateLimiter | None = None
    paddle_client: PaddleOcrClient | None = None

    for engine in engines:
        if engine == ENGINE_OPENTYPHOON:
            opentyphoon_limiter = opentyphoon_limiter or OcrRateLimiter()
        elif engine == ENGINE_PADDLE:
            paddle_client = paddle_client or PaddleOcrClient()

        for image_path in images:
            preprocess = (
                prepare_meter_display_image(image_path, debug_dir)
                if preprocess_enabled
                else None
            )
            ocr_image_path = (
                preprocess.ocr_image_path
                if preprocess and preprocess.used_crop and use_crop_for_ocr
                else image_path
            )
            if engine == ENGINE_OPENTYPHOON and opentyphoon_limiter:
                ocr_result = await opentyphoon_limiter.read_image(str(ocr_image_path))
            elif engine == ENGINE_PADDLE and paddle_client:
                ocr_result = await asyncio.to_thread(
                    paddle_client.read_image,
                    str(ocr_image_path),
                )
            else:
                raise ValueError(f"Unsupported OCR engine: {engine}")

            raw_text = ocr_result.raw_text if ocr_result.success else ""
            parsed = parse_meter_value(raw_text)
            expected = labels.get(image_path.name)
            confidence = score_ocr_reading(
                meter_id=expected.meter_id if expected else "",
                parsed_value=parsed.value,
                parse_reason=parsed.reason or "",
                raw_text=raw_text,
                parse_confidence=parsed.confidence,
                unit=parsed.unit,
                candidates=parsed.candidates,
                use_history=False,
            )
            rows.append(
                EvaluationRow(
                    engine=engine,
                    image_path=image_path,
                    ocr_image_path=ocr_image_path,
                    expected=expected,
                    raw_text=raw_text,
                    parsed=parsed,
                    confidence_level=confidence.level,
                    confidence_reason=confidence.reason,
                    confidence_warnings=confidence.warnings,
                    preprocess=preprocess,
                    duration_ms=ocr_result.duration_ms,
                    error=ocr_result.error,
                )
            )
    return rows


def write_report(
    rows: list[EvaluationRow],
    image_dir: Path,
    labels_path: Path | None,
    report_dir: Path,
    timezone_name: str,
    generated_at: datetime | None = None,
) -> Path:
    report_dir.mkdir(parents=True, exist_ok=True)

    now = generated_at or datetime.now(ZoneInfo(timezone_name))
    report_path = report_dir / f"ocr-evaluation-{now.strftime('%Y%m%d-%H%M%S')}.md"
    content = build_report(rows, image_dir, labels_path, now)
    report_path.write_text(content, encoding="utf-8")
    return report_path


def build_report(
    rows: list[EvaluationRow],
    image_dir: Path,
    labels_path: Path | None,
    generated_at: datetime,
) -> str:
    total = len(rows)
    ocr_success = sum(1 for row in rows if row.error is None)
    parsed_count = sum(1 for row in rows if row.parsed_value is not None)
    labeled_rows = [row for row in rows if row.expected is not None]
    correct_count = sum(1 for row in labeled_rows if row.correct is True)
    engines = sorted({row.engine for row in rows})
    accuracy_text = (
        format_accuracy(correct_count, len(labeled_rows))
        if labeled_rows
        else "not calculated (no labels file)"
    )

    lines = [
        "# OCR Evaluation Report",
        "",
        f"- Generated: {generated_at.isoformat(timespec='seconds')}",
        f"- Image directory: `{image_dir}`",
        f"- Labels file: `{labels_path}`" if labels_path else "- Labels file: not found",
        f"- Engines: `{', '.join(engines)}`",
        f"- Total OCR attempts: {total}",
        f"- OCR success: {ocr_success}/{total}",
        f"- Parsed value: {parsed_count}/{total}",
        f"- Exact accuracy: {accuracy_text}",
        f"- Parser mode: `{PARSER_MODE}`",
        "",
    ]

    lines.extend(["## Engine Accuracy", ""])
    lines.extend(
        [
            "| Engine | OCR Success | Parsed | Exact Accuracy |",
            "| --- | ---: | ---: | ---: |",
        ]
    )
    for engine in engines:
        engine_rows = [row for row in rows if row.engine == engine]
        engine_labeled = [row for row in engine_rows if row.expected is not None]
        engine_correct = sum(1 for row in engine_labeled if row.correct is True)
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_escape(engine),
                    f"{sum(1 for row in engine_rows if row.error is None)}/{len(engine_rows)}",
                    f"{sum(1 for row in engine_rows if row.parsed_value is not None)}/{len(engine_rows)}",
                    format_accuracy(engine_correct, len(engine_labeled))
                    if engine_labeled
                    else "not calculated",
                ]
            )
            + " |"
        )
    lines.append("")

    if not labeled_rows:
        lines.extend(
            [
                "## Label File Format",
                "",
                "Create `tmp/test-ocr/labels.csv` when the expected values are ready:",
                "",
                "```csv",
                "file,meter_id,expected_value",
                "1.jpg,M1,12508",
                "2.jpg,M2,12610",
                "```",
                "",
            ]
        )

    lines.extend(
        [
            "## Summary",
            "",
            "| Engine | Image | Meter | Expected | Parsed | Correct | Source | Unit | Confidence | Reason | Preprocess | OCR Image | Crop Size | Candidates | Status | Duration |",
            "| --- | --- | --- | ---: | ---: | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---: |",
        ]
    )

    for row in rows:
        expected_value = row.expected.value if row.expected else ""
        meter_id = row.expected.meter_id if row.expected else ""
        parsed_value = row.parsed_value if row.parsed_value is not None else ""
        correct = format_correct(row.correct)
        candidates = ", ".join(format_decimal(value) for value in row.parsed.candidates)
        status = "ok" if row.error is None else f"error: {row.error}"
        lines.append(
            "| "
            + " | ".join(
                [
                    markdown_escape(row.engine),
                    markdown_escape(row.image_path.name),
                    markdown_escape(meter_id),
                    markdown_escape(format_decimal(expected_value)),
                    markdown_escape(format_decimal(parsed_value)),
                    correct,
                    markdown_escape(row.parsed.source_label or ""),
                    markdown_escape(row.parsed.unit or ""),
                    markdown_escape(row.confidence_level),
                    markdown_escape(row.confidence_reason),
                    markdown_escape(format_preprocess(row.preprocess, row.ocr_image_path)),
                    markdown_escape(str(row.ocr_image_path)),
                    markdown_escape(format_crop_size(row.preprocess)),
                    markdown_escape(candidates),
                    markdown_escape(status),
                    f"{row.duration_ms} ms",
                ]
            )
            + " |"
        )

    lines.extend(["", "## Raw OCR", ""])
    for row in rows:
        lines.extend(
            [
                f"### {row.engine} / {row.image_path.name}",
                "",
                f"- Parsed: `{format_decimal(row.parsed_value)}`",
                f"- Expected: `{format_decimal(row.expected.value)}`"
                if row.expected
                else "- Expected: not labeled",
                f"- Source: `{row.parsed.source_label or ''}`",
                f"- Unit: `{row.parsed.unit or ''}`",
                f"- Confidence: `{row.confidence_level}`",
                f"- Reason: `{row.confidence_reason}`",
                f"- Warnings: `{'; '.join(row.confidence_warnings)}`",
                f"- Preprocess: `{format_preprocess(row.preprocess, row.ocr_image_path)}`",
                f"- OCR image: `{row.ocr_image_path}`",
                f"- Crop size: `{format_crop_size(row.preprocess)}`",
                f"- Status: `{row.error or 'ok'}`",
                "",
                "```text",
                row.raw_text.strip() or "(empty)",
                "```",
                "",
            ]
        )

    return "\n".join(lines)


def format_accuracy(correct: int, total: int) -> str:
    if total == 0:
        return "not calculated"
    percent = (Decimal(correct) / Decimal(total)) * Decimal(100)
    return f"{correct}/{total} ({percent.quantize(Decimal('0.01'))}%)"


def format_correct(value: bool | None) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "-"


def format_decimal(value) -> str:
    if value is None:
        return ""
    if value == "":
        return ""
    return str(value)


def format_preprocess(
    preprocess: PreprocessResult | None,
    ocr_image_path: Path | None = None,
) -> str:
    if preprocess is None:
        return "disabled"
    if preprocess.used_crop:
        if ocr_image_path and preprocess.crop_path and ocr_image_path == preprocess.crop_path:
            return "crop_used_for_ocr"
        return "debug_crop"
    return f"full_image_fallback:{preprocess.reason}"


def format_crop_size(preprocess: PreprocessResult | None) -> str:
    if not preprocess or not preprocess.crop_size:
        return ""
    return f"{preprocess.crop_size[0]}x{preprocess.crop_size[1]}"


def markdown_escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")


async def run() -> Path:
    args = parse_args()
    generated_at = datetime.now(ZoneInfo(args.timezone))
    images = find_images(args.image_dir, args.limit)
    labels_path = resolve_labels_path(args.image_dir, args.labels)
    labels = load_labels(labels_path)
    engines = parse_engines(args.engine)
    debug_dir = args.debug_dir / generated_at.strftime("%Y%m%d-%H%M%S")

    rows = await evaluate_images(
        images=images,
        labels=labels,
        engines=engines,
        preprocess_enabled=args.preprocess,
        use_crop_for_ocr=args.use_crop_for_ocr,
        debug_dir=debug_dir,
    )
    return write_report(
        rows=rows,
        image_dir=args.image_dir,
        labels_path=labels_path,
        report_dir=args.report_dir,
        timezone_name=args.timezone,
        generated_at=generated_at,
    )


if __name__ == "__main__":
    path = asyncio.run(run())
    print(f"OCR evaluation report: {path}")
