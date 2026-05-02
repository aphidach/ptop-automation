from __future__ import annotations

import logging
import time

from app.ocr.opentyphoon import OcrResult

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "paddleocr"


class PaddleOcrClient:
    def __init__(self, lang: str = "en"):
        self.lang = lang
        self._ocr = None

    def read_image(self, image_path: str) -> OcrResult:
        started_at = time.monotonic()
        try:
            ocr = self._get_ocr()
            result = ocr.ocr(image_path, cls=True)
            raw_text = _flatten_paddle_result(result)
            return OcrResult(
                raw_text=raw_text,
                model=DEFAULT_MODEL,
                duration_ms=int((time.monotonic() - started_at) * 1000),
            )
        except ModuleNotFoundError:
            return OcrResult(
                model=DEFAULT_MODEL,
                duration_ms=int((time.monotonic() - started_at) * 1000),
                error="paddleocr package is not installed",
            )
        except Exception as exc:
            logger.exception("PaddleOCR failed")
            return OcrResult(
                model=DEFAULT_MODEL,
                duration_ms=int((time.monotonic() - started_at) * 1000),
                error=str(exc),
            )

    def _get_ocr(self):
        if self._ocr is None:
            from paddleocr import PaddleOCR

            self._ocr = PaddleOCR(use_angle_cls=True, lang=self.lang)
        return self._ocr


def _flatten_paddle_result(result) -> str:
    lines: list[str] = []
    for page in result or []:
        for item in page or []:
            if not item or len(item) < 2:
                continue
            text_info = item[1]
            if isinstance(text_info, (list, tuple)) and text_info:
                lines.append(str(text_info[0]))
    return "\n".join(lines)
