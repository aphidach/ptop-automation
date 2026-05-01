# OCR Model: OpenTyphoon

## Selected Model

Use:

```text
typhoon-ocr
```

Reason:

- Latest recommended OpenTyphoon OCR endpoint
- Supports PNG, JPEG, and PDF
- Optimized for Thai and English document/image text extraction
- Official rate limit: 2 requests/second and 20 requests/minute

Reference:

- https://docs.opentyphoon.ai/en/ocr/
- https://docs.opentyphoon.ai/en/rate-limits/

## Package Option

OpenTyphoon provides a Python helper package:

```bash
pip install typhoon-ocr
```

Environment variable:

```bash
TYPHOON_OCR_API_KEY=your_api_key_here
```

Example:

```python
from typhoon_ocr import ocr_document

markdown = ocr_document(
    pdf_or_image_path="meter.jpg"
)
```

## API Compatibility Option

OpenTyphoon API is OpenAI-compatible.

Base URL:

```text
https://api.opentyphoon.ai/v1
```

Authentication:

```text
Authorization: Bearer <TYPHOON_API_KEY>
```

For this project, prefer the `typhoon-ocr` helper first because it is built for OCR images/PDFs directly.

## Rate Limit Design

Official limits for `typhoon-ocr`:

| limit | value |
| --- | ---: |
| requests per second | 2 |
| requests per minute | 20 |

The minute limit is the stricter one for sustained usage. For safe MVP behavior:

- Use one global OCR queue
- Never run more than 2 OCR requests in the same second
- Never run more than 20 OCR requests in a rolling minute
- Add retry with exponential backoff on 429/rate-limit errors
- Keep OCR jobs idempotent by storing `message_id` and `image_hash`

## Queue Recommendation

For 8 meter images, a simple queue is enough.

```mermaid
flowchart LR
    A["LINE image event"] --> B["Create OCR job"]
    B --> C["OCR queue"]
    C --> D["Rate limiter 2 r/s + 20 r/min"]
    D --> E["OpenTyphoon typhoon-ocr"]
    E --> F["Parse value"]
    F --> G["Pending confirmation"]
```

Suggested Python interface:

```python
class OcrClient:
    def read_meter_value(self, image_path: str) -> "OcrResult":
        ...

class OcrResult:
    raw_text: str
    parsed_value: int | None
    model: str = "typhoon-ocr"
```

## Meter Value Extraction

OCR returns markdown/text, not a guaranteed single number. The backend should parse carefully.

Recommended parser:

1. Normalize Thai/English digits and separators
2. Extract numeric candidates such as `12,500`, `12500`, `012500`
3. Remove commas/spaces
4. Reject tiny numbers unrelated to meter value if needed
5. Prefer the largest plausible meter-like number
6. Ask for manual entry if no plausible number exists

Example:

```python
import re

def parse_meter_value(raw_text: str) -> int | None:
    candidates = re.findall(r"\d[\d, ]{2,}", raw_text)
    values = []
    for candidate in candidates:
        normalized = candidate.replace(",", "").replace(" ", "")
        if normalized.isdigit():
            values.append(int(normalized))
    plausible = [value for value in values if value >= 100]
    return max(plausible) if plausible else None
```

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

## Retry Policy

Recommended retry rules:

| error | action |
| --- | --- |
| 429 rate limit | retry with exponential backoff |
| 5xx API error | retry up to 3 times |
| timeout | retry up to 2 times |
| invalid image | ask user to resend image |
| unreadable OCR | ask user for manual value |

Backoff example:

```text
1s -> 2s -> 4s -> 8s
```

## Logging

Store these fields for debugging:

- `model`
- `request_started_at`
- `request_finished_at`
- `duration_ms`
- `image_message_id`
- `raw_text`
- `parsed_value`
- `error_code`
- `retry_count`
