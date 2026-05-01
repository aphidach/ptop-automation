import asyncio
import logging
import time
from collections import deque

from app.config import settings
from app.ocr.opentyphoon import OcrResult, TyphoonOcrClient

logger = logging.getLogger(__name__)


class OcrRateLimiter:
    def __init__(
        self,
        client: TyphoonOcrClient | None = None,
        burst_limit: int | None = None,
        sustained_limit: int | None = None,
        max_retries: int | None = None,
    ):
        self.client = client or TyphoonOcrClient()
        self.burst_limit = burst_limit or settings.OCR_RATE_LIMIT_BURST
        self.sustained_limit = sustained_limit or settings.OCR_RATE_LIMIT_SUSTAINED
        self.max_retries = max_retries or settings.OCR_RATE_LIMIT_MAX_RETRIES

        self._lock = asyncio.Lock()
        self._burst_timestamps: deque[float] = deque()
        self._sustained_timestamps: deque[float] = deque()

    def _prune_timestamps(self, now: float) -> None:
        while self._burst_timestamps and self._burst_timestamps[0] <= now - 1.0:
            self._burst_timestamps.popleft()
        while self._sustained_timestamps and self._sustained_timestamps[0] <= now - 60.0:
            self._sustained_timestamps.popleft()

    async def _acquire(self) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                self._prune_timestamps(now)

                burst_wait = 0.0
                if len(self._burst_timestamps) >= self.burst_limit:
                    burst_wait = self._burst_timestamps[0] - (now - 1.0) + 0.01

                sustained_wait = 0.0
                if len(self._sustained_timestamps) >= self.sustained_limit:
                    sustained_wait = self._sustained_timestamps[0] - (now - 60.0) + 0.01

                wait = max(burst_wait, sustained_wait)
                if wait <= 0:
                    self._burst_timestamps.append(now)
                    self._sustained_timestamps.append(now)
                    return

            logger.debug("Rate limiter waiting %.2fs", wait)
            await asyncio.sleep(wait)

    async def read_image(self, image_path: str) -> OcrResult:
        await self._acquire()

        for attempt in range(1, self.max_retries + 1):
            result = await asyncio.to_thread(self.client.read_image, image_path)

            if not result.error or not result.error.startswith("HTTP 429"):
                return result

            if attempt < self.max_retries:
                backoff = 2 ** attempt
                logger.warning(
                    "OCR rate limited (429), retry %d/%d in %ds",
                    attempt,
                    self.max_retries,
                    backoff,
                )
                await asyncio.sleep(backoff)
                await self._acquire()
            else:
                logger.error(
                    "OCR rate limited (429), max retries (%d) exceeded",
                    self.max_retries,
                )

        return result
