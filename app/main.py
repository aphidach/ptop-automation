from fastapi import FastAPI

from app.config import settings
from app.line.webhook import router as line_webhook_router

app = FastAPI(title=settings.APP_NAME)
app.include_router(line_webhook_router)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "solar-meter-bot"}
