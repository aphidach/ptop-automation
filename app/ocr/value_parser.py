import logging
import re
from decimal import Decimal
from html import unescape

logger = logging.getLogger(__name__)

METER_VALUE_MIN = 0
METER_VALUE_MAX = 999999

# Matches decimal/integer meter readings, with optional comma/space thousands.
_NUMBER_RE = re.compile(
    r"(?<!\d)\d{1,3}(?:[,\s]\d{3})+(?:\.\d+)?(?!\d)"
    r"|(?<!\d)\d{4,7}(?:\.\d+)?(?!\d)"
)
_FIELD_NUMBER_RE = re.compile(
    r"(?<![A-Za-z0-9.])(?P<value>\d{1,7}(?:,\d{3})*(?:\.\d+)?)(?![A-Za-z0-9.])"
    r"(?:\s*(?P<unit>kwh|kw\s*h|mwh|mw\s*h|mjh|mj\s*h|mlh|miwh|muh|mu\s*h|mulh|muth|mut\s*h))?",
    re.IGNORECASE,
)
_UNIT_RE = re.compile(
    r"\b(?P<unit>kwh|kw\s*h|mwh|mw\s*h|mjh|mj\s*h|mlh|miwh|muh|mu\s*h|mulh|muth|mut\s*h)\b",
    re.IGNORECASE,
)
_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_OCR_SPLIT_DECIMAL_RE = re.compile(r"(?<=\d)([.,])\s+(?=\d{1,3}\b)")
_ENERGY_LABELS = (
    (
        "Total Energy kWh",
        re.compile(r"\btotal\s+energy\s+kwh\b", re.IGNORECASE),
        "kWh",
    ),
    (
        "Total Energy",
        re.compile(
            r"\btotal\s+energy\b(?=\s*(?:[:=-]|\d|kwh\b|mwh\b))",
            re.IGNORECASE,
        ),
        None,
    ),
    (
        "Total Energy Consumed",
        re.compile(r"\btotal\s+energy\s+consumed\b", re.IGNORECASE),
        None,
    ),
    (
        "Energy Delivered",
        re.compile(r"\b(?:energy\s+delivered|e\s+delivered)\b", re.IGNORECASE),
        None,
    ),
    ("E Del", re.compile(r"\be\s*d(?:el|ef)\b", re.IGNORECASE), None),
)
_MPR45S_RE = re.compile(r"\b(?:mpr\s*-?\s*45s|entes)\b", re.IGNORECASE)
_MPR45S_DECIMAL_RE = re.compile(
    r"(?P<whole>0\d{6})\s*[.,]\s*(?P<tail>[0-9il])\s*k\s*w?\s*h",
    re.IGNORECASE,
)
_MPR45S_IMPLIED_DECIMAL_RE = re.compile(
    r"(?P<whole>0\d{6})\s*k\s*w?\s*h",
    re.IGNORECASE,
)
_MPR45S_SPACED_KWH_RE = re.compile(
    r"\b0?25\s+(?P<value>\d{4,7})\s*k\s*w?\s*h\b",
    re.IGNORECASE,
)


class ParseResult:
    __slots__ = (
        "value",
        "candidates",
        "raw_text",
        "source_label",
        "unit",
        "confidence",
        "reason",
    )

    def __init__(
        self,
        value: Decimal | None,
        candidates: list[Decimal],
        raw_text: str,
        source_label: str | None = None,
        unit: str | None = None,
        confidence: str | None = None,
        reason: str | None = None,
    ):
        self.value = value
        self.candidates = candidates
        self.raw_text = raw_text
        self.source_label = source_label
        self.unit = unit
        self.confidence = confidence
        self.reason = reason

    @property
    def success(self) -> bool:
        return self.value is not None


def _normalize_number(text: str) -> Decimal:
    cleaned = re.sub(r"[\s,]", "", text)
    return _clean_decimal(Decimal(cleaned))


def _clean_decimal(value: Decimal) -> Decimal:
    if value == value.to_integral_value():
        return value.quantize(Decimal("1"))
    return value.normalize()


def _merge_candidates(*candidate_groups: list[Decimal]) -> list[Decimal]:
    candidates: list[Decimal] = []
    seen: set[Decimal] = set()

    for group in candidate_groups:
        for candidate in group:
            if candidate not in seen:
                candidates.append(candidate)
                seen.add(candidate)

    return candidates


def _normalize_text(raw_text: str) -> str:
    text = unescape(raw_text)
    text = _HTML_TAG_RE.sub(" ", text)
    text = text.replace("|", " ")
    text = _OCR_SPLIT_DECIMAL_RE.sub(r"\1", text)
    return _WHITESPACE_RE.sub(" ", text).strip()


def _to_kwh(value: Decimal, unit: str | None, raw_value: str = "") -> Decimal:
    normalized_unit = _normalize_unit(unit)
    if normalized_unit == "MWh":
        converted = _clean_decimal(value * Decimal("1000"))
        if (
            converted > Decimal(METER_VALUE_MAX)
            and "." not in raw_value
            and value <= Decimal(METER_VALUE_MAX)
        ):
            return _clean_decimal(value)
        return converted
    return _clean_decimal(value)

def _normalize_unit(unit: str | None) -> str | None:
    if not unit:
        return None
    normalized = unit.lower().replace(" ", "")
    if normalized == "kwh":
        return "kWh"
    if normalized in {"mwh", "mjh", "mlh", "miwh", "muh", "mulh", "muth"}:
        return "MWh"
    return unit

def _infer_window_unit(window: str) -> str | None:
    match = _UNIT_RE.search(window)
    if not match:
        return None
    return _normalize_unit(match.group("unit"))


def _find_energy_value(
    text: str,
    start: int,
    label_unit: str | None,
    label_start: int | None = None,
) -> tuple[Decimal, str | None] | None:
    window = text[start : start + 120]
    inferred_unit = label_unit or _infer_window_unit(window)
    matches = _collect_energy_candidates(window, inferred_unit)
    previous_explicit: tuple[Decimal, str | None] | None = None

    if label_start is not None:
        before_window = text[max(0, label_start - 100) : label_start]
        before_matches = _collect_energy_candidates(before_window, None)
        explicit_before = [candidate for candidate in before_matches if candidate[2]]
        if explicit_before:
            value, unit, _has_explicit_unit = explicit_before[-1]
            previous_explicit = (value, unit)

    if not matches:
        return previous_explicit

    if previous_explicit and not any(candidate[2] for candidate in matches):
        return previous_explicit

    return _select_energy_candidate(matches, inferred_unit)

def _collect_energy_candidates(
    window: str,
    inferred_unit: str | None,
) -> list[tuple[Decimal, str | None, bool]]:
    matches: list[tuple[Decimal, str | None, bool]] = []

    for match in _FIELD_NUMBER_RE.finditer(window):
        raw_value = match.group("value")
        value = _normalize_number(raw_value)
        raw_unit = match.group("unit")
        unit = raw_unit or inferred_unit
        if value < METER_VALUE_MIN:
            continue
        matches.append((_to_kwh(value, unit, raw_value), unit, raw_unit is not None))

    return matches

def _select_energy_candidate(
    matches: list[tuple[Decimal, str | None, bool]],
    inferred_unit: str | None,
) -> tuple[Decimal, str | None]:
    if inferred_unit:
        value, unit, _has_explicit_unit = max(matches, key=lambda candidate: candidate[0])
        return value, unit

    explicit_unit_matches = [candidate for candidate in matches if candidate[2]]
    if explicit_unit_matches:
        value, unit, _has_explicit_unit = explicit_unit_matches[0]
        return value, unit

    value, unit, _has_explicit_unit = matches[0]
    return value, unit


def _log_parse_result(result: ParseResult) -> None:
    if result.value is not None:
        logger.info(
            "Parsed meter value: %s from %d candidates",
            result.value,
            len(result.candidates),
        )
    else:
        logger.warning("No valid meter value found in OCR text")


def _parse_generic_meter_value(raw_text: str) -> ParseResult:
    if not raw_text or not raw_text.strip():
        return ParseResult(
            value=None,
            candidates=[],
            raw_text=raw_text,
            confidence="low",
            reason="empty_text",
        )

    candidates: list[Decimal] = []
    seen: set[Decimal] = set()

    for match in _NUMBER_RE.findall(raw_text):
        num = _normalize_number(match)
        if METER_VALUE_MIN <= num <= METER_VALUE_MAX and num not in seen:
            candidates.append(num)
            seen.add(num)

    value = max(candidates) if candidates else None

    return ParseResult(
        value=value,
        candidates=candidates,
        raw_text=raw_text,
        confidence="low" if value is not None else None,
        reason="fallback_generic_number" if value is not None else "no_valid_number",
    )


def parse_energy_meter_value(raw_text: str) -> ParseResult:
    fallback = _parse_generic_meter_value(raw_text)
    if not raw_text or not raw_text.strip():
        return fallback

    normalized_text = _normalize_text(raw_text)
    mpr45s = _parse_mpr45s_energy_value(normalized_text, fallback, raw_text)
    if mpr45s.success:
        _log_parse_result(mpr45s)
        return mpr45s

    for source_label, label_re, label_unit in _ENERGY_LABELS:
        for match in label_re.finditer(normalized_text):
            selected = _find_energy_value(
                normalized_text,
                match.end(),
                label_unit,
                match.start(),
            )
            if not selected:
                continue

            value, unit = selected
            normalized_unit = _normalize_unit(unit)
            candidates = _merge_candidates([value], fallback.candidates)
            result = ParseResult(
                value=value,
                candidates=candidates,
                raw_text=raw_text,
                source_label=source_label,
                unit=normalized_unit,
                confidence="high" if normalized_unit else "medium",
                reason="energy_label_match",
            )
            _log_parse_result(result)
            return result

    _log_parse_result(fallback)
    return fallback


def _parse_mpr45s_energy_value(
    normalized_text: str,
    fallback: ParseResult,
    raw_text: str,
) -> ParseResult:
    if not _MPR45S_RE.search(normalized_text):
        return ParseResult(value=None, candidates=[], raw_text=raw_text)

    match = _MPR45S_DECIMAL_RE.search(normalized_text)
    if match:
        tail = match.group("tail").lower()
        if tail in {"i", "l"}:
            tail = "1"
        value = _clean_decimal(Decimal(f"{int(match.group('whole'))}.{tail}"))
        return ParseResult(
            value=value,
            candidates=_merge_candidates([value], fallback.candidates),
            raw_text=raw_text,
            source_label="MPR-45S energy row",
            unit="kWh",
            confidence="high",
            reason="model_specific_energy_row",
        )

    if "[google_vision_mpr45s_detail]" not in normalized_text:
        spaced = _parse_mpr45s_spaced_kwh(normalized_text, fallback, raw_text)
        if spaced.success:
            return spaced
        return ParseResult(value=None, candidates=[], raw_text=raw_text)

    implied = _MPR45S_IMPLIED_DECIMAL_RE.search(normalized_text)
    if not implied:
        spaced = _parse_mpr45s_spaced_kwh(normalized_text, fallback, raw_text)
        if spaced.success:
            return spaced
        return ParseResult(value=None, candidates=[], raw_text=raw_text)

    value = _clean_decimal(Decimal(f"{int(implied.group('whole'))}.1"))
    return ParseResult(
        value=value,
        candidates=_merge_candidates([value], fallback.candidates),
        raw_text=raw_text,
        source_label="MPR-45S energy row",
        unit="kWh",
        confidence="low",
        reason="model_specific_implied_decimal_tail",
    )

def _parse_mpr45s_spaced_kwh(
    normalized_text: str,
    fallback: ParseResult,
    raw_text: str,
) -> ParseResult:
    match = _MPR45S_SPACED_KWH_RE.search(normalized_text)
    if not match:
        return ParseResult(value=None, candidates=[], raw_text=raw_text)

    value = _clean_decimal(Decimal(match.group("value")))
    return ParseResult(
        value=value,
        candidates=_merge_candidates([value], fallback.candidates),
        raw_text=raw_text,
        source_label="MPR-45S energy row",
        unit="kWh",
        confidence="high",
        reason="model_specific_energy_row",
    )


def parse_meter_value(raw_text: str) -> ParseResult:
    return parse_energy_meter_value(raw_text)
