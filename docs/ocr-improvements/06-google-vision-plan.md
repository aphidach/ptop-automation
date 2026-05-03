# Implement 06: Google Vision OCR

## Goal

Use Google Cloud Vision as the production OCR engine for LINE meter images.

## Current Status

Implemented and selected as the production path.

Latest real-image evaluation:

- Dataset: `tmp/test-ocr`
- Report: `reports/ocr/ocr-evaluation-20260503-014420.md`
- OCR success: `8/8`
- Parsed value: `8/8`
- Exact accuracy: `8/8`

## Assumptions

- Cloud Vision API is already enabled.
- The existing `GOOGLE_APPLICATION_CREDENTIALS` service account used for Google Sheets can also call Cloud Vision.
- The same parser, confidence gate, and evaluation report should be reused.
- Low-confidence OCR values still require user confirmation or manual correction before saving.

## Why Google Vision

The latest OpenTyphoon baseline after parser improvements was:

- OCR success: 8/8
- Parsed value: 8/8
- Exact accuracy: 6/8

Google Vision improved the difficult cases and now reaches `8/8` on the current fixture. It is also operationally simpler because the app already uses a Google service account for Sheets.

Remaining caveat:

- `5.jpg`: correct after `MPR-45S` detail crop/parser handling, but still low confidence because the decimal tail is visually unclear.

## Implementation Scope

### 1. Dependency

Included in `requirements.txt`:

```text
google-cloud-vision
```

### 2. OCR Client

Implemented in:

```text
app/ocr/google_vision.py
```

Runtime interface:

```python
class GoogleVisionOcrClient:
    def read_image(self, image_path: str) -> OcrResult:
        ...
```

Return the existing `OcrResult` type from:

```text
app/ocr/opentyphoon.py
```

### 3. Use Document Text Detection

Use `DOCUMENT_TEXT_DETECTION`, not generic `TEXT_DETECTION`.

Reason:

- Meter screens contain dense structured rows.
- Labels and values are arranged like a small table.
- This aligns better with the existing field-aware parser.

### 4. Convert Response to Raw Text

Current implementation uses:

```text
response.full_text_annotation.text
```

Future upgrade: keep block/paragraph/word bounding boxes for improved pairing:

```text
E Del -> nearest numeric value on same row
Total Energy -> nearest value after label
```

### 5. Connect Evaluator

Implemented in:

```text
scripts/evaluate_ocr.py
```

Main commands:

```bash
rtk uv run python scripts/evaluate_ocr.py --engine google
rtk uv run python scripts/evaluate_ocr.py --engine opentyphoon,google
```

Report should include:

- engine
- raw text
- parsed value
- source label
- unit
- confidence
- duration
- exact accuracy

## Test Plan

Run:

```bash
rtk uv run pytest tests/test_google_vision_ocr.py tests/test_value_parser.py tests/test_ocr_confidence.py tests/test_evaluate_ocr.py
rtk uv run python scripts/evaluate_ocr.py --engine google
rtk uv run pytest
```

Focus on:

- `5.jpg`: does the `MPR-45S` detail crop/parser return `250509.1` and mark the risk?
- `7.jpg`: does parser normalize the delivered energy row to `61270`?
- `8.jpg`: does unit normalization preserve the intended energy value?

## Decision Rule

Use Google Vision as production default while:

- exact accuracy remains `8/8` on `tmp/test-ocr`, and
- remaining failures are low confidence, not silently wrong

Otherwise:

- keep confirmation/manual correction for low-confidence values
- add model-specific parser/crop handling only for measured failures
- compare another OCR engine only if Google Vision regresses on real images

## Production Follow-Up

Production flow already uses `GoogleVisionOcrClient`.

Keep:

1. One Google service account for Sheets and Vision.
2. Cloud Vision API enabled for that service account project.
3. User confirmation for all normal OCR readings.
4. Manual review flow for low-confidence readings.

## Success Criteria

- `--engine google` creates a Markdown report.
- `--engine google` reaches `8/8` on the tracked fixture.
- Google Vision failures are visible as report rows, not runtime crashes.
- Production LINE flow uses Google Vision and never saves OCR values without confirmation.
