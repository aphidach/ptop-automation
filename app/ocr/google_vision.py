from __future__ import annotations

from io import BytesIO
import logging
import time

from PIL import Image, ImageEnhance, ImageOps

from app.ocr.opentyphoon import OcrResult
from app.ocr.preprocess import _detect_dark_display_region

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "google-vision-document-text-detection"


class GoogleVisionOcrClient:
    def __init__(
        self,
        client=None,
        model: str = DEFAULT_MODEL,
        enable_mpr45s_detail_crop: bool = True,
    ):
        self._client = client
        self.model = model
        self.enable_mpr45s_detail_crop = enable_mpr45s_detail_crop

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
            detail_text = self._read_mpr45s_detail_crop(image_path, raw_text)
            if detail_text:
                raw_text = f"{raw_text}\n\n[google_vision_mpr45s_detail]\n{detail_text}"
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

    def _read_mpr45s_detail_crop(self, image_path: str, raw_text: str) -> str:
        if not self.enable_mpr45s_detail_crop or not _looks_like_mpr45s(raw_text):
            return ""

        content = _make_mpr45s_detail_crop(image_path)
        if not content:
            return ""

        try:
            response = self._get_client().document_text_detection(
                image=self._make_image(content)
            )
        except Exception:
            logger.exception("Google Vision MPR-45S detail crop OCR failed")
            return ""

        error_message = getattr(getattr(response, "error", None), "message", "")
        if error_message:
            logger.warning("Google Vision MPR-45S detail crop failed: %s", error_message)
            return ""

        annotation = getattr(response, "full_text_annotation", None)
        return getattr(annotation, "text", "").strip() if annotation else ""


def _looks_like_mpr45s(raw_text: str) -> bool:
    compact = raw_text.lower().replace(" ", "")
    return "mpr-45s" in compact or "mpr45s" in compact or "entes" in compact


def _make_mpr45s_detail_crop(image_path: str) -> bytes:
    try:
        image = Image.open(image_path).convert("RGB")
    except Exception:
        logger.exception("Failed to open image for MPR-45S detail crop")
        return b""

    box = _detect_dark_display_region(image)
    display = image.crop(box) if box else image
    width, height = display.size
    crop = display.crop(
        (
            int(width * 0.08),
            int(height * 0.54),
            int(width * 0.95),
            int(height * 0.74),
        )
    )

    scale = 1800 / max(crop.size)
    if scale > 1:
        crop = crop.resize(
            (int(crop.width * scale), int(crop.height * scale)),
            Image.Resampling.LANCZOS,
        )

    crop = ImageOps.grayscale(crop)
    crop = ImageOps.autocontrast(crop, cutoff=1)
    crop = ImageEnhance.Contrast(crop).enhance(1.5)

    output = BytesIO()
    crop.save(output, format="PNG")
    return output.getvalue()
