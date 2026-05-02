# Implement 06: Google Vision OCR Plan

## Goal

Add Google Cloud Vision as an OCR engine for comparison against OpenTyphoon before changing the production LINE flow.

## Assumptions

- Cloud Vision API is already enabled.
- The existing `GOOGLE_APPLICATION_CREDENTIALS` service account used for Google Sheets can also call Cloud Vision.
- The same parser, confidence gate, and evaluation report should be reused.
- Production should not switch to Google Vision until the real-image report proves it is better.

## Why Add Google Vision

The latest OpenTyphoon baseline after parser improvements is:

- OCR success: 8/8
- Parsed value: 8/8
- Exact accuracy: 6/8

Remaining difficult cases:

- `5.jpg`: OCR loses the decimal tail, reading `250509` instead of `250509.1`
- `7.jpg`: OCR misplaces the decimal/unit around `Energy Delivered`

Google Vision may help because its OCR response includes structured text annotations and bounding boxes. That can support better label-value pairing later, especially for fields like `E Del` on the left and values on the right.

## Implementation Scope

### 1. Add Dependency

Add to `requirements.txt`:

```text
google-cloud-vision
```

### 2. Add OCR Client

Create:

```text
app/ocr/google_vision.py
```

Recommended interface:

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

Start with `DOCUMENT_TEXT_DETECTION`, not generic `TEXT_DETECTION`.

Reason:

- Meter screens contain dense structured rows.
- Labels and values are arranged like a small table.
- This aligns better with the existing field-aware parser.

### 4. Convert Response to Raw Text

First implementation can use:

```text
response.full_text_annotation.text
```

Later, keep block/paragraph/word bounding boxes for improved pairing:

```text
E Del -> nearest numeric value on same row
Total Energy -> nearest value after label
```

### 5. Connect Evaluator

Update:

```text
scripts/evaluate_ocr.py
```

Add engine name:

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
rtk uv run pytest tests/test_value_parser.py tests/test_ocr_confidence.py
rtk uv run python scripts/evaluate_ocr.py --engine google
rtk uv run python scripts/evaluate_ocr.py --engine opentyphoon,google
```

Focus on:

- `5.jpg`: does Google Vision read `250509.1`?
- `7.jpg`: does Google Vision read `61.270 MWh`, `61270`, or `612.70 MWh`?
- `8.jpg`: does Google Vision preserve `MWh` instead of misreading it as `MJh`?

## Decision Rule

Use Google Vision as production default only if:

- exact accuracy is at least 7/8 on `tmp/test-ocr`, and
- remaining failures are low confidence, not silently wrong

Otherwise:

- keep OpenTyphoon as default
- use Google Vision as fallback for low-confidence cases
- or keep it as an evaluation-only engine

## Production Follow-Up

Only after comparison proves useful:

1. Add environment config:

```env
OCR_ENGINE=opentyphoon
```

Allowed values:

```text
opentyphoon
google
fallback
```

2. Update OCR client selection in production flow.
3. If `fallback`, call Google Vision only when OpenTyphoon returns low-confidence output.
4. Keep user confirmation for all OCR readings.

## Success Criteria

- `--engine google` creates a Markdown report.
- `--engine opentyphoon,google` compares both engines in one report.
- Google Vision failures are visible as report rows, not runtime crashes.
- Production LINE flow remains unchanged until a report proves Google Vision is better.
