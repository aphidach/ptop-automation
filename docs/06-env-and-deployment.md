# Environment and Deployment

## Required Environment Variables

```bash
APP_ENV=development
APP_VERSION=0.3.1
APP_BASE_URL=https://your-domain.example.com
LOG_LEVEL=INFO
TIMEZONE=Asia/Bangkok

LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
LINE_CHANNEL_SECRET=your_line_channel_secret

GOOGLE_APPLICATION_CREDENTIALS=credentials/google-service-account.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id

OCR_MAX_PRODUCED_UNIT_KWH=10000

REPORT_IMAGE_STORAGE=local

EXPECTED_METER_COUNT=8
DEFAULT_RATE=4.2
```

## Release Image

Release and package steps are maintained in [Release and Packaging](10-release-and-packaging.md).

Tagged releases publish Docker images to GitHub Container Registry:

```text
ghcr.io/<owner>/<repo>:0.3.1
```

## Local Development

Recommended tools:

```bash
rtk make install
rtk make run
```

Expose local webhook with a tunnel such as ngrok or Cloudflare Tunnel:

```bash
ngrok http 8000
```

Set LINE webhook URL:

```text
https://your-tunnel-url/webhook/line
```

## Google Sheets Setup

1. Create a Google Cloud project
2. Enable Google Sheets API
3. Enable Cloud Vision API
4. Create a service account
5. Download service account JSON
6. Place it at `credentials/google-service-account.json`
7. Create the spreadsheet tabs from `docs/02-google-sheets-schema.md`
8. Share the spreadsheet with the service account email as Editor

The same service account is used for both Google Sheets and Google Vision. If OCR fails with a Google API permission error, check that Cloud Vision API is enabled in the same Google Cloud project as the service account.

Never commit the credential JSON file.

Recommended `.gitignore` entries:

```gitignore
.env
.venv/
credentials/*.json
tmp/
reports/
```

## LINE Setup

1. Create LINE Messaging API channel
2. Copy channel secret and channel access token
3. Enable webhook
4. Disable auto-reply if it conflicts with bot responses
5. Set webhook endpoint to `/webhook/line`
6. Verify webhook

Webhook endpoint must validate the LINE signature.

Set LINE allowlists before production use:

```text
ALLOWED_LINE_SOURCE_IDS=Cxxxxxxxx,Uxxxxxxxx
ALLOWED_LINE_USER_IDS=Uxxxxxxxx,Uyyyyyyyy
```

`ALLOWED_LINE_SOURCE_IDS` controls allowed chats: group IDs, room IDs, or direct user chat IDs. `ALLOWED_LINE_USER_IDS` controls allowed senders. When both are set, the event must match both lists before the bot replies.

## Deployment Options

Good MVP options:

- Render
- Railway
- Fly.io
- Google Cloud Run
- A small VPS

For production, Cloud Run is a strong fit because Google Sheets and service account integration are straightforward.

## Runtime Components

Minimum:

- FastAPI web server
- Background OCR queue in same process
- Google Sheets as durable storage

Better:

- FastAPI web server
- Redis queue/session store
- Worker process for OCR
- Google Sheets for business records

## Production Checklist

- LINE signature verification enabled
- Allowed source ids configured
- OCR queue rate limit enabled
- Retry and dead-letter logging enabled
- Google credentials stored securely
- `/api/ocr/test` protected or disabled
- Report image hosting strategy decided
- Health check endpoint configured
- Logs include request ids and LINE event ids

## Report Image Delivery

LINE image messages usually require an accessible image URL. Recommended options:

- Upload generated report image to Cloudflare R2 and send its public HTTPS URL
- Upload generated report image to Google Cloud Storage and send the public or signed URL
- For MVP, use a simple static file endpoint if the backend is publicly reachable

Do not rely on local file paths for LINE delivery in production.

### Cloudflare R2

Report images use local static hosting by default:

```bash
REPORT_IMAGE_STORAGE=local
```

To send report images through Cloudflare R2, create an R2 bucket, configure a public or custom HTTPS domain for that bucket, create an R2 access key with write access to the bucket, then set:

```bash
REPORT_IMAGE_STORAGE=r2
R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=your_r2_access_key_id
R2_SECRET_ACCESS_KEY=your_r2_secret_access_key
R2_BUCKET=your_r2_bucket
R2_PUBLIC_URL=https://your-public-r2-domain.example.com
```

Generated reports are uploaded to `reports/{batch_id}.png`, and the LINE image message uses `R2_PUBLIC_URL/reports/{batch_id}.png`.

`R2_ENDPOINT` must be the account-level S3 API endpoint only. Do not append the bucket name because `R2_BUCKET` is configured separately.
