# System Architecture

## High-Level Architecture

```mermaid
flowchart TD
    U["LINE User"] --> L["LINE Messaging API"]
    L --> W["FastAPI /webhook/line"]
    W --> S["Conversation Session Service"]
    W --> C["LINE Content Downloader"]
    C --> O["Google Vision OCR"]
    O --> P["Meter Value Parser"]
    P --> H["Human Confirmation Flow"]
    H --> G["Google Sheets Client"]
    G --> R["Report Generator"]
    R --> B["LINE Reply / Push Message"]
    B --> U
```

## Recommended Backend Modules

```text
app/
  main.py
  config.py
  line/
    webhook.py
    client.py
    parser.py
  ocr/
    google_vision.py
    value_parser.py
  sheets/
    client.py
    repositories.py
  report/
    generator.py
    templates.py
  services/
    meter_service.py
    batch_service.py
    confirmation_service.py
  models/
    domain.py
    schemas.py
```

## Request Flow: Image Reading

```mermaid
sequenceDiagram
    participant User
    participant LINE
    participant API as Python Backend
    participant OCR as Google Vision OCR
    participant Sheet as Google Sheets

    User->>LINE: Send "M1"
    LINE->>API: Text webhook event
    API->>API: Store latest meter_id=M1 for user
    API-->>User: Reply "ส่งรูป M1 ได้เลย"

    User->>LINE: Send image
    LINE->>API: Image webhook event
    API->>LINE: Download image by message_id
    API->>OCR: OCR image
    OCR-->>API: Text result
    API->>API: Extract numeric meter value
    API-->>User: Confirm "M1 = 12500, OK?"

    User->>LINE: Send "OK"
    LINE->>API: Text webhook event
    API->>Sheet: Append confirmed reading
    API->>Sheet: Check batch completeness
    API-->>User: Reply saved or send report if complete
```

## State Management

Google Sheets is enough for durable business data, but conversation state should not live only in memory if deployment can restart.

Recommended MVP options:

- Simple MVP: in-memory session dict, acceptable only for local demo
- Better MVP: SQLite or Redis for `latest_meter_id`, `pending_confirmation`, `batch_id`
- Production: Redis for short-lived conversation state plus Google Sheets for durable readings

## Batch Strategy

Use one weekly batch per LINE group or user.

Recommended `batch_id` format:

```text
{yyyy}-W{ww}-{line_source_id}
```

Example:

```text
2026-W19-Uxxxxxxxx
```

## Error Handling Strategy

- OCR timeout: tell user to retry image
- OCR unreadable: ask user to type value manually, e.g. `M1 12508`
- Unknown meter id: ask user to type meter id first
- Duplicate reading in same batch: ask whether to replace previous value
- Google Sheets write failure: keep pending confirmation and ask user to retry `OK`
- LINE reply failure: log event and use push message if possible

## Security Boundaries

- LINE webhook signature must be verified before processing
- Secrets must be stored in environment variables, not in source code
- Google service account JSON must not be committed
- Only allowed LINE users/groups should be able to write readings
- Dev-only endpoints must be disabled or protected in production
