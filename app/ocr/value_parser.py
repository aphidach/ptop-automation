import logging
import re

logger = logging.getLogger(__name__)

METER_VALUE_MIN = 0
METER_VALUE_MAX = 999999

# Matches comma/space-separated thousands (e.g. 12,500 or 12 500)
# or plain 4-7 digit numbers (e.g. 12500, 012500)
_NUMBER_RE = re.compile(
    r"(?<!\d)\d{1,3}(?:[,\s]\d{3})+(?!\d)" r"|(?<!\d)\d{4,7}(?!\d)"
)


class ParseResult:
    __slots__ = ("value", "candidates", "raw_text")

    def __init__(
        self, value: int | None, candidates: list[int], raw_text: str
    ):
        self.value = value
        self.candidates = candidates
        self.raw_text = raw_text

    @property
    def success(self) -> bool:
        return self.value is not None


def _normalize_number(text: str) -> int:
    cleaned = text.replace(",", "").replace(" ", "")
    return int(cleaned)


def parse_meter_value(raw_text: str) -> ParseResult:
    if not raw_text or not raw_text.strip():
        return ParseResult(value=None, candidates=[], raw_text=raw_text)

    candidates: list[int] = []
    seen: set[int] = set()

    for match in _NUMBER_RE.findall(raw_text):
        num = _normalize_number(match)
        if METER_VALUE_MIN <= num <= METER_VALUE_MAX and num not in seen:
            candidates.append(num)
            seen.add(num)

    value = max(candidates) if candidates else None

    if value is not None:
        logger.info(
            "Parsed meter value: %d from %d candidates", value, len(candidates)
        )
    else:
        logger.warning("No valid meter value found in OCR text")

    return ParseResult(value=value, candidates=candidates, raw_text=raw_text)
