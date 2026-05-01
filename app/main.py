from fastapi import FastAPI

from app.config import settings
from app.line.webhook import router as line_webhook_router

app = FastAPI(title=settings.APP_NAME)
app.include_router(line_webhook_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "solar-meter-bot"}


@app.get("/api/sheets/health")
async def sheets_health():
    try:
        from app.sheets.client import sheets_client

        meters = sheets_client.get_active_meters()
        return {
            "status": "ok",
            "meters_count": len(meters),
            "meter_ids": [m.get("meter_id") for m in meters],
        }
    except Exception as e:
        return {"status": "error", "detail": str(e)}
