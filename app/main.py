import asyncio
from contextlib import asynccontextmanager, suppress
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.logging_config import configure_logging

configure_logging()

from app.line.webhook import router as line_webhook_router
from app.storage import sync as storage_sync
from app.storage.sqlite import sqlite_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    sqlite_client.setup()
    sync_task: asyncio.Task | None = None
    if settings.SHEETS_SYNC_ENABLED:
        if settings.SHEETS_STARTUP_PULL_ENABLED:
            await asyncio.to_thread(storage_sync.pull_business_config_from_sheets)
        await asyncio.to_thread(storage_sync.flush_outbox)
        sync_task = asyncio.create_task(storage_sync.periodic_sync_loop())

    try:
        yield
    finally:
        if sync_task:
            sync_task.cancel()
            with suppress(asyncio.CancelledError):
                await sync_task


def create_app() -> FastAPI:
    fastapi_app = FastAPI(
        title=settings.APP_NAME,
        version=settings.APP_VERSION,
        lifespan=lifespan,
    )
    fastapi_app.include_router(line_webhook_router)

    report_dir = Path(settings.REPORT_DIR)
    report_dir.mkdir(parents=True, exist_ok=True)
    fastapi_app.mount("/reports", StaticFiles(directory=str(report_dir)), name="reports")
    fastapi_app.get("/health")(health)
    fastapi_app.get("/api/sheets/health")(sheets_health)
    fastapi_app.get("/api/storage/sync/health")(storage_sync_health)
    return fastapi_app


async def health():
    return {"status": "ok", "service": settings.APP_NAME, "version": settings.APP_VERSION}


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


async def storage_sync_health():
    return storage_sync.health()


app = create_app()
