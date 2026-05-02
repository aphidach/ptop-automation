# OCR Improvement Implementation Map

## Current Baseline

Latest real-image evaluation:

- Test images: `tmp/test-ocr/*.jpg`
- Labels: `tmp/test-ocr/labels.csv`
- Report: `reports/ocr/ocr-evaluation-20260503-001012.md`
- OCR success: 8/8
- Parsed value: 7/8
- Exact accuracy: 1/8

Main finding: OCR often sees the correct text, but the parser selects the wrong numeric field. The current strategy effectively prefers the largest plausible-looking number, which is unsafe for meter screens containing voltage, current, power, date, and energy values.

## Implementation Order

1. `01-field-aware-energy-parser.md`
2. `02-data-labeling-evaluation-loop.md`
3. `03-confidence-plausibility-gate.md`
4. `04-roi-display-preprocessing.md`
5. `05-ocr-engine-comparison.md`

This order is intentional. The first fix is likely to improve accuracy fastest because the correct `E Del` / `Total Energy` values are already present in many raw OCR outputs.

## Research-Informed Direction

Meter-reading research usually treats AMR as a pipeline:

```text
detect display/counter -> crop/rectify -> recognize text/digits -> parse target field -> validate reading
```

Useful references:

- Copel-AMR uses real field images and includes counter corner annotations for rectification plus digit bounding boxes: https://github.com/raysonlaroca/copel-amr-dataset
- Dryad 2026 water meter dataset separates detection/segmentation images from recognition crops and labels: https://datadryad.org/dataset/doi%3A10.5061/dryad.7d7wm3860
- PaddleOCR exposes detection, orientation, unwarping, and recognition as separate modules: https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html
- OpenTyphoon OCR returns structured, layout-aware Markdown for images and PDFs: https://docs.opentyphoon.ai/en/ocr/

## Success Target

Short-term target:

- Exact accuracy on `tmp/test-ocr`: at least 6/8 after field-aware parser
- No automatic save without user confirmation
- Every OCR test run creates a Markdown report

Medium-term target:

- Exact accuracy: at least 7/8 on current sample
- Low-confidence readings are clearly marked for manual confirmation
- New images can be labeled and evaluated without code changes
