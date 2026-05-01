# MVP Roadmap

## Phase 1: Project Skeleton

- Create FastAPI app
- Add config loading from `.env`
- Add `/health`
- Add LINE webhook route
- Verify LINE signature
- Add basic logging

Done when:

- LINE webhook verification succeeds
- `/health` returns `ok`

## Phase 2: LINE Image Intake

- Handle text messages
- Store latest meter id per user/source
- Handle image messages
- Download image by LINE `message_id`
- Save temporary image file

Done when:

- User can type `M1`
- User can send an image
- Backend downloads the image successfully

## Phase 3: OpenTyphoon OCR

- Add `typhoon-ocr` package
- Add `TYPHOON_OCR_API_KEY`
- Implement OCR client
- Implement global rate limiter for 2 r/s and 20 r/min
- Implement meter value parser

Done when:

- Backend can OCR a local test image
- Parsed value is returned or marked unreadable

## Phase 4: Confirmation Flow

- Store pending confirmation
- Reply OCR result to LINE
- Support `OK`
- Support correction format `M1 12508`
- Support `CANCEL`

Done when:

- No OCR value is written to Google Sheets until user confirms

## Phase 5: Google Sheets Integration

- Create spreadsheet tabs
- Implement meters repository
- Implement readings repository
- Implement last reading lookup
- Append confirmed reading
- Calculate produced units and amount

Done when:

- Confirmed values appear in `readings`
- Calculated fields are correct

## Phase 6: Batch and Report

- Create or find weekly batch
- Track progress 1/8 through 8/8
- Generate report image with table and totals
- Send report image to LINE

Done when:

- After the 8th confirmed meter, LINE receives a report image

## Phase 7: Hardening

- Add duplicate reading replacement flow
- Add retry and dead-letter logging for OCR
- Add `STATUS`, `REPORT`, and `HELP`
- Add source allowlist
- Add deployment docs and runbook

Done when:

- Field use is safe enough for real weekly readings

## Suggested Requirements

```txt
fastapi
uvicorn[standard]
python-dotenv
line-bot-sdk
gspread
google-auth
typhoon-ocr
pydantic
pydantic-settings
pandas
matplotlib
pillow
tenacity
```

## Implementation Order

Recommended order:

1. LINE webhook and text command handling
2. Image download
3. OCR client and rate limiter
4. Confirmation flow
5. Google Sheets append
6. Report image generation
7. Deployment

This avoids building the report layer before the data capture path is proven.
