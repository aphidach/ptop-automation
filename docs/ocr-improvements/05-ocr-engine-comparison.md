# Implement 05: OCR Engine Comparison

## Goal

Document the OCR engine decision after comparing OpenTyphoon and Google Vision.

## Current Decision

Google Vision is now the production OCR engine.

Latest Google Vision result:

- Dataset: `tmp/test-ocr`
- Report: `reports/ocr/ocr-evaluation-20260503-014420.md`
- Exact accuracy: `8/8`

OpenTyphoon remains available only as a legacy comparison path in the evaluator.

## Candidate Engines

### Google Vision

Strengths:

- Production now shares the same Google service account used for Sheets
- `DOCUMENT_TEXT_DETECTION` works well for dense meter rows
- Response can provide text annotations and bounding boxes for future field/value pairing
- Current real-image fixture reaches `8/8`

Limitations:

- Can miss tiny decimal tails on low-contrast LCD rows
- Some cases still need model-specific crop/parser logic and low-confidence review

### OpenTyphoon

Strengths:

- Current integration already exists
- Produces structured, layout-aware Markdown
- Handles mixed Thai/English document-like images

Limitations for this task:

- Output is text/Markdown, not a stable display-region bounding box API
- May hallucinate explanatory figure text around the device

Reference: https://docs.opentyphoon.ai/en/ocr/

### PaddleOCR

Strengths:

- Pipeline separates orientation, unwarping, text detection, and text recognition
- Detection boxes can help associate labels and values spatially
- Useful as a local comparison engine

Limitations:

- Extra dependency and model download
- May need tuning for small LCD digits and low contrast

Reference: https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html

## First Comparison Design

Production already uses Google Vision. Keep comparison runs as developer-only checks.

Add an optional evaluator mode:

```bash
rtk uv run python scripts/evaluate_ocr.py --engine google
rtk uv run python scripts/evaluate_ocr.py --engine opentyphoon,google
```

Report both:

- raw output
- parsed value
- selected field
- exact accuracy
- duration

## What To Compare

For each image:

- Did engine read the target energy row?
- Did engine preserve the decimal point?
- Did engine preserve the unit?
- Did engine include distracting non-screen text?
- Did parser select the correct value?

## Decision Rule

Keep Google Vision as production default while it maintains `8/8` on the tracked fixture and sends low-confidence readings to user review.

Consider another engine only if it improves one of these:

- detects/crops display lines better
- preserves decimal points better
- reduces hallucinated/explanatory text
- gives bounding boxes that improve field/value pairing

## Verification

Run:

```bash
rtk make ocr-test
```

Then run the optional comparison command once implemented.

Success criteria:

- Comparison report clearly shows engine-by-engine accuracy
- Production LINE behavior stays on Google Vision unless a better engine path is proven
