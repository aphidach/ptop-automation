# Implement 02: Data Labeling and Evaluation Loop

## Goal

Make every OCR improvement measurable using real images, expected values, and Markdown reports.

## Current State

Already available:

- Images: `tmp/test-ocr/1.jpg` to `tmp/test-ocr/8.jpg`
- Labels: `tmp/test-ocr/labels.csv`
- Batch evaluator: `scripts/evaluate_ocr.py`
- Make target: `rtk make ocr-test`
- Reports: `reports/ocr/*.md`

## Label Format

Use `kWh` as the canonical expected value.

```csv
file,meter_id,expected_value
1.jpg,M1,58196
2.jpg,M2,60601
```

If the display shows `MWh`, convert to `kWh` in the label.

Examples:

- `58.196 MWh` -> `58196`
- `84.352 MWh` -> `84352`
- `135420.05 kWh` -> `135420.05`

## Recommended Enhancements

Add these fields to future reports:

- parser version or mode
- selected source label, such as `E Del` or `Total Energy`
- selected unit, such as `MWh` or `kWh`
- normalized value in `kWh`
- confidence level: `high`, `medium`, `low`
- reason, such as `energy_label_match` or `fallback_generic_number`

## Why This Matters

Research datasets such as Copel-AMR and the Dryad 2026 water meter dataset separate labels and evaluation from model implementation. That makes it possible to improve detection, recognition, and parsing independently.

This project should do the same at a smaller scale:

```text
real image -> OCR output -> parser output -> expected label -> report
```

## Implementation Notes

Keep `reports/ocr/` ignored by git if these are run artifacts. Keep `tmp/test-ocr/labels.csv` tracked or copied into a stable docs fixture if the team wants reproducible test data.

Possible next file:

- `tests/fixtures/ocr/raw_outputs/*.txt`

This would let parser tests run without calling the OpenTyphoon API every time.

## Verification

Run:

```bash
rtk make ocr-test
```

Success criteria:

- A new `.md` report is created for every run
- Accuracy is calculated when `labels.csv` exists
- Report clearly separates OCR failures from parser failures
