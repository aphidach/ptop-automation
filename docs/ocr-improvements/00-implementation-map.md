# OCR Improvement Implementation Map

## Current Baseline

Latest real-image evaluation:

- Test images: `tmp/test-ocr/*.jpg`
- Labels: `tmp/test-ocr/labels.csv`
- Engine: Google Vision
- Report: `reports/ocr/ocr-evaluation-20260503-014420.md`
- OCR success: 8/8
- Parsed value: 8/8
- Exact accuracy: 8/8

Main finding: Google Vision plus field-aware parsing is good enough for the current 8-image fixture. The remaining production risk is not silent accuracy on the fixture, but low-confidence edge cases such as the `ENTES MPR-45S` decimal tail in `5.jpg`.

## Implementation Order

1. `01-field-aware-energy-parser.md`
2. `02-data-labeling-evaluation-loop.md`
3. `03-confidence-plausibility-gate.md`
4. `04-roi-display-preprocessing.md`
5. `05-ocr-engine-comparison.md`
6. `06-google-vision-plan.md`

This order is now mostly implemented for the current dataset. Future work should keep the same loop: label real images, run Google Vision evaluation, inspect low-confidence/fail cases, then add the narrowest parser or crop rule needed.

## Research-Informed Direction

Meter-reading research usually treats AMR as a pipeline:

```text
detect display/counter -> crop/rectify -> recognize text/digits -> parse target field -> validate reading
```

Useful references:

- Copel-AMR uses real field images and includes counter corner annotations for rectification plus digit bounding boxes: https://github.com/raysonlaroca/copel-amr-dataset
- Dryad 2026 water meter dataset separates detection/segmentation images from recognition crops and labels: https://datadryad.org/dataset/doi%3A10.5061/dryad.7d7wm3860
- PaddleOCR exposes detection, orientation, unwarping, and recognition as separate modules: https://www.paddleocr.ai/main/en/version3.x/pipeline_usage/OCR.html
- Google Vision OCR provides document text detection and text annotations: https://cloud.google.com/vision/docs/ocr
- OpenTyphoon OCR remains useful as a legacy comparison engine: https://docs.opentyphoon.ai/en/ocr/

## Success Target

Short-term target:

- Exact accuracy on `tmp/test-ocr`: 8/8 with Google Vision
- No automatic save without user confirmation
- Every OCR test run creates a Markdown report

Medium-term target:

- Add more real images per meter model and keep exact accuracy at 8/8 for the tracked fixture
- Low-confidence readings are clearly marked for manual confirmation
- New images can be labeled and evaluated without code changes
