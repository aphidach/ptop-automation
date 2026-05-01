# Backend API Spec

## Base

Recommended framework:

```text
FastAPI
```

Recommended local URL:

```text
http://localhost:8000
```

## Public Endpoints

### GET /health

Health check for deployment platform.

Response:

```json
{
  "status": "ok",
  "service": "solar-meter-bot"
}
```

### POST /webhook/line

LINE Messaging API webhook endpoint.

Important requirements:

- Verify `X-Line-Signature`
- Return HTTP 200 quickly
- Do expensive OCR processing in a background task or queue

Headers:

| header | required | notes |
| --- | --- | --- |
| X-Line-Signature | yes | Used to verify LINE request |

Request body:

```json
{
  "destination": "xxxxxxxxxx",
  "events": [
    {
      "type": "message",
      "message": {
        "type": "image",
        "id": "1234567890"
      },
      "replyToken": "reply-token",
      "source": {
        "type": "user",
        "userId": "Uxxxx"
      },
      "timestamp": 1777856400000
    }
  ]
}
```

Response:

```json
{
  "ok": true
}
```

## Internal / Admin Endpoints

These endpoints are optional and should be protected or disabled in production.

### POST /api/readings/manual

Manually add a confirmed meter reading.

Request:

```json
{
  "line_source_id": "Uxxxx",
  "line_user_id": "Uxxxx",
  "meter_id": "M1",
  "current_value": 12508,
  "date": "2026-05-04",
  "rate": 4.2,
  "confirmation_method": "manual_entry"
}
```

Response:

```json
{
  "reading_id": "rdg_20260504_M1",
  "batch_id": "2026-W19-Uxxxx",
  "meter_id": "M1",
  "current_value": 12508,
  "last_value": 12000,
  "produced_unit": 508,
  "amount": 2133.6
}
```

### POST /api/ocr/test

Developer-only OCR test endpoint.

Request:

```json
{
  "image_url": "https://example.com/meter.jpg",
  "meter_id": "M1"
}
```

Response:

```json
{
  "meter_id": "M1",
  "ocr_value": 12500,
  "ocr_raw_text": "12500",
  "confidence": null
}
```

### GET /api/batches/{batch_id}

Returns batch progress.

Response:

```json
{
  "batch_id": "2026-W19-Uxxxx",
  "week": "2026-W19",
  "status": "collecting",
  "expected_meter_count": 8,
  "confirmed_meter_count": 6,
  "missing_meter_ids": ["M7", "M8"]
}
```

### POST /api/batches/{batch_id}/report

Regenerate a report image for a batch.

Response:

```json
{
  "batch_id": "2026-W19-Uxxxx",
  "status": "reported",
  "report_image_path": "/tmp/reports/2026-W19-Uxxxx.png"
}
```

## LINE Message Handling Rules

### Text: meter id

Input:

```text
M1
```

Behavior:

- Validate `M1` exists in `meters`
- Store `latest_meter_id=M1` in session
- Reply: `รับทราบ M1 ส่งรูปได้เลยครับ`

### Text: OK

Behavior:

- Find latest pending confirmation for this user/source
- Save confirmed reading
- Reply saved summary
- If batch complete, generate and send report

### Text: manual correction

Input:

```text
M1 12508
```

Behavior:

- Validate meter id and numeric value
- Save or update pending confirmation as manual edit
- Append confirmed reading

### Image

Behavior:

- Resolve meter id from image caption if available, otherwise from latest session meter id
- Download image content from LINE
- Send image to OCR queue
- Parse numeric value
- Reply confirmation message

## Background Jobs

Recommended jobs:

- `process_ocr_job(message_id, meter_id, source_id, user_id, batch_id)`
- `expire_pending_confirmations()`
- `generate_report_if_batch_complete(batch_id)`

## Response Time Targets

- `/webhook/line`: less than 1 second for acknowledgement
- OCR result reply: usually less than 30 seconds for 8 images, depending on rate limit and API latency
- Report generation: less than 10 seconds after final confirmation
