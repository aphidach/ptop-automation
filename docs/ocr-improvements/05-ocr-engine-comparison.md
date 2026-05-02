# Implement 05: OCR Engine Comparison

## Goal

Compare OpenTyphoon against at least one OCR engine that returns text locations or line-level outputs, without replacing the production OCR path immediately.

## Why This Is Later

The current baseline shows OpenTyphoon already reads useful text from all 8 images. The main failure is choosing the wrong value. Engine comparison should come after field-aware parsing and confidence scoring.

## Candidate Engines

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

Do not change production behavior yet.

Add an optional evaluator mode:

```bash
rtk uv run python scripts/evaluate_ocr.py --engine opentyphoon
rtk uv run python scripts/evaluate_ocr.py --engine paddle
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

Keep OpenTyphoon if field-aware parser reaches target accuracy.

Add PaddleOCR only if it improves one of these:

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
- No production LINE behavior changes until a better engine path is proven
