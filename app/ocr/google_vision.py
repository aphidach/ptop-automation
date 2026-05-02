from __future__ import annotations

import logging
import time

from app.ocr.opentyphoon import OcrResult

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "google-vision-document-text-detection"


class GoogleVisionOcrClient:
    def __init__(self, client=None, model: str = DEFAULT_MODEL):
        self._client = client
        self.model = model

    def read_image(self, image_path: str) -> OcrResult:
        started_at = time.monotonic()

        try:
            with open(image_path, "rb") as f:
                content = f.read()

            image = self._make_image(content)
            response = self._get_client().document_text_detection(image=image)
            duration_ms = int((time.monotonic() - started_at) * 1000)

            error_message = getattr(getattr(response, "error", None), "message", "")
            if error_message:
                logger.error("Google Vision OCR failed: %s", error_message)
                return OcrResult(
                    model=self.model,
                    duration_ms=duration_ms,
                    error=f"Google Vision error: {error_message}",
                )

            annotation = getattr(response, "full_text_annotation", None)
            raw_text = getattr(annotation, "text", "") if annotation else ""
            logger.info(
                "Google Vision OCR completed: duration_ms=%d text_len=%d",
                duration_ms,
                len(raw_text),
            )
            return OcrResult(
                raw_text=raw_text,
                model=self.model,
                duration_ms=duration_ms,
            )

        except ModuleNotFoundError:
            duration_ms = int((time.monotonic() - started_at) * 1000)
            return OcrResult(
                model=self.model,
                duration_ms=duration_ms,
                error="google-cloud-vision package is not installed",
            )
        except FileNotFoundError:
            duration_ms = int((time.monotonic() - started_at) * 1000)
            return OcrResult(
                model=self.model,
                duration_ms=duration_ms,
                error=f"Image file not found: {image_path}",
            )
        except Exception as exc:
            duration_ms = int((time.monotonic() - started_at) * 1000)
            logger.exception("Google Vision OCR failed")
            return OcrResult(
                model=self.model,
                duration_ms=duration_ms,
                error=str(exc),
            )

    def _get_client(self):
        if self._client is None:
            from google.cloud import vision

            self._client = vision.ImageAnnotatorClient()
        return self._client

    def _make_image(self, content: bytes):
        from google.cloud import vision

        return vision.Image(content=content)
