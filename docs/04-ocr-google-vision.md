# OCR Model: Google Vision

## Selected Model

Use Google Cloud Vision `DOCUMENT_TEXT_DETECTION` through:

```text
google-cloud-vision
```

Reason:

- Production LINE OCR is standardized on one Google service account.
- Meter screens contain dense structured rows, so document text detection is a better starting point than generic text detection.
- The response includes text annotations and bounding boxes that can support better label-value pairing later.

Reference:

- https://cloud.google.com/vision/docs/ocr

## Environment

Use the same service account credential path already used for Google Sheets:

```bash
GOOGLE_APPLICATION_CREDENTIALS=credentials/google-service-account.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id
```

The Google Cloud project for that service account must have Cloud Vision API enabled.

## Runtime Behavior

The LINE production flow uses:

```text
app/ocr/google_vision.py
```

The OCR client returns the existing `OcrResult` shape so parser, confidence, confirmation, and audit behavior stay unchanged.

## Confirmation Is Required

Do not append the OCR value immediately.

Bot message:

```text
อ่านค่าได้:
M1 = 12,500

ยืนยันไหม?
พิมพ์: OK
หรือแก้เป็น: M1 12508
```

If OCR fails:

```text
ผมอ่านเลขจากรูปนี้ไม่ชัดครับ
กรุณาพิมพ์ค่าเอง เช่น:
M1 12508
```

## Evaluation

OpenTyphoon can still be used by the developer evaluator for comparison:

```bash
rtk uv run python scripts/evaluate_ocr.py --engine google
rtk uv run python scripts/evaluate_ocr.py --engine opentyphoon,google
```
