from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.line.webhook import router as line_webhook_router

app = FastAPI(title=settings.APP_NAME, version=settings.APP_VERSION)
app.include_router(line_webhook_router)

# Serve report images via static endpoint (MVP approach)
report_dir = Path(settings.REPORT_DIR)
report_dir.mkdir(parents=True, exist_ok=True)
app.mount("/reports", StaticFiles(directory=str(report_dir)), name="reports")


@app.get("/health")
async def health():
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}


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
