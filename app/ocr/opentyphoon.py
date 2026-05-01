import json
import logging
import time

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

API_URL = "https://api.opentyphoon.ai/v1/ocr"
DEFAULT_MODEL = "typhoon-ocr"
DEFAULT_TASK_TYPE = "default"
DEFAULT_MAX_TOKENS = 16384
DEFAULT_TEMPERATURE = 0.1
DEFAULT_TOP_P = 0.6
DEFAULT_REPETITION_PENALTY = 1.2


class OcrResult:
    __slots__ = ("raw_text", "model", "duration_ms", "error")

    def __init__(
        self,
        raw_text: str = "",
        model: str = DEFAULT_MODEL,
        duration_ms: int = 0,
        error: str | None = None,
    ):
        self.raw_text = raw_text
        self.model = model
        self.duration_ms = duration_ms
        self.error = error

    @property
    def success(self) -> bool:
        return self.error is None


class TyphoonOcrClient:
    def __init__(
        self,
        api_key: str | None = None,
        model: str = DEFAULT_MODEL,
        task_type: str = DEFAULT_TASK_TYPE,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        temperature: float = DEFAULT_TEMPERATURE,
        top_p: float = DEFAULT_TOP_P,
        repetition_penalty: float = DEFAULT_REPETITION_PENALTY,
    ):
        self.api_key = api_key or settings.TYPHOON_OCR_API_KEY
        self.model = model
        self.task_type = task_type
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.repetition_penalty = repetition_penalty

    def read_image(self, image_path: str) -> OcrResult:
        started_at = time.monotonic()

        try:
            with open(image_path, "rb") as f:
                files = {"file": f}
                data = {
                    "model": self.model,
                    "task_type": self.task_type,
                    "max_tokens": str(self.max_tokens),
                    "temperature": str(self.temperature),
                    "top_p": str(self.top_p),
                    "repetition_penalty": str(self.repetition_penalty),
                }
                headers = {"Authorization": f"Bearer {self.api_key}"}

                response = httpx.post(
                    API_URL,
                    files=files,
                    data=data,
                    headers=headers,
                    timeout=120.0,
                )

            duration_ms = int((time.monotonic() - started_at) * 1000)

            if response.status_code != 200:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error("OCR request failed: %s", error_msg)
                return OcrResult(
                    model=self.model,
                    duration_ms=duration_ms,
                    error=error_msg,
                )

            result = response.json()
            extracted_texts = []

            for page_result in result.get("results", []):
                if page_result.get("success") and page_result.get("message"):
                    content = page_result["message"]["choices"][0]["message"]["content"]
                    try:
                        parsed = json.loads(content)
                        text = parsed.get("natural_text", content)
                    except (json.JSONDecodeError, KeyError):
                        text = content
                    extracted_texts.append(text)
                elif not page_result.get("success"):
                    logger.warning(
                        "OCR page error: %s",
                        page_result.get("error", "Unknown error"),
                    )

            raw_text = "\n".join(extracted_texts)
            logger.info(
                "OCR completed: model=%s duration_ms=%d text_len=%d",
                self.model,
                duration_ms,
                len(raw_text),
            )

            return OcrResult(
                raw_text=raw_text,
                model=self.model,
                duration_ms=duration_ms,
            )

        except httpx.TimeoutException:
            duration_ms = int((time.monotonic() - started_at) * 1000)
            logger.error("OCR request timed out after %dms", duration_ms)
            return OcrResult(
                model=self.model,
                duration_ms=duration_ms,
                error="Request timed out",
            )
        except FileNotFoundError:
            return OcrResult(error=f"Image file not found: {image_path}")
        except Exception as e:
            duration_ms = int((time.monotonic() - started_at) * 1000)
            logger.error("OCR unexpected error: %s", e)
            return OcrResult(
                model=self.model,
                duration_ms=duration_ms,
                error=str(e),
            )
