from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Sequence

from app.config import settings
from app.ocr.value_parser import METER_VALUE_MAX
from app.sheets import repositories

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"
DEFAULT_MAX_PRODUCED_KWH = Decimal("10000")


@dataclass
class ConfidenceResult:
    level: str
    reason: str
    warnings: list[str]
    last_value: Decimal | None = None
    produced_unit: Decimal | None = None

    @property
    def is_low(self) -> bool:
        return self.level == CONFIDENCE_LOW


def score_ocr_reading(
    meter_id: str,
    parsed_value: Decimal | None,
    parse_reason: str,
    raw_text: str,
    *,
    line_source_id: str | None = None,
    parse_confidence: str | None = None,
    unit: str | None = None,
    candidates: Sequence[Decimal] | None = None,
    last_value: Decimal | None = None,
    use_history: bool = True,
    max_produced_unit: Decimal | None = None,
) -> ConfidenceResult:
    warnings: list[str] = []

    if parsed_value is None:
        return ConfidenceResult(
            level=CONFIDENCE_LOW,
            reason="no_parsed_value",
            warnings=["อ่านค่า OCR ไม่ได้"],
        )

    max_produced = max_produced_unit or _get_max_produced_unit()
    previous = last_value if last_value is not None else None
    if previous is None and use_history and meter_id:
        previous = _get_last_value(meter_id, line_source_id)
    produced = parsed_value - previous if previous is not None else None

    if parse_reason == "fallback_generic_number":
        warnings.append("ใช้ตัวเลขสำรอง เพราะไม่พบป้ายกำกับพลังงาน")

    if parse_reason == "model_specific_implied_decimal_tail":
        warnings.append("ทศนิยมท้าย MPR-45S ไม่ชัด ใช้รูปแบบจอช่วยตีความ")

    if parsed_value > Decimal(METER_VALUE_MAX):
        warnings.append(f"ค่าที่อ่านได้สูงเกินช่วงที่รองรับ ({METER_VALUE_MAX} kWh)")

    if unit == "MWh" and parsed_value >= Decimal("200000"):
        warnings.append("ค่า MWh ที่แปลงแล้วสูงมาก ควรตรวจสอบจุดทศนิยม")

    if produced is not None:
        if produced < 0:
            warnings.append(
                f"ค่าปัจจุบัน ({parsed_value}) น้อยกว่าครั้งก่อน ({previous})"
            )
        elif previous > 0 and produced > max_produced:
            warnings.append(
                f"ผลิตเพิ่ม {produced} kWh สูงกว่าเกณฑ์ตรวจสอบ {max_produced} kWh"
            )

    if _has_conflicting_candidates(parsed_value, candidates):
        warnings.append("พบตัวเลข OCR หลายค่าที่ต่างกันมาก")

    if warnings:
        return ConfidenceResult(
            level=CONFIDENCE_LOW,
            reason="plausibility_warning",
            warnings=warnings,
            last_value=previous,
            produced_unit=produced,
        )

    if parse_reason in {"energy_label_match", "model_specific_energy_row"} and unit:
        return ConfidenceResult(
            level=CONFIDENCE_HIGH,
            reason="energy_label_unit_plausible",
            warnings=[],
            last_value=previous,
            produced_unit=produced,
        )

    if (
        parse_reason in {"energy_label_match", "model_specific_energy_row"}
        or parse_confidence == CONFIDENCE_MEDIUM
    ):
        return ConfidenceResult(
            level=CONFIDENCE_MEDIUM,
            reason="energy_label_without_unit",
            warnings=["พบป้ายกำกับพลังงาน แต่หน่วยไม่ชัดเจน"],
            last_value=previous,
            produced_unit=produced,
        )

    return ConfidenceResult(
        level=CONFIDENCE_LOW,
        reason="low_parse_confidence",
        warnings=["ผล OCR ยังไม่น่าเชื่อถือพอสำหรับการยืนยันปกติ"],
        last_value=previous,
        produced_unit=produced,
    )


def _get_last_value(meter_id: str, line_source_id: str | None = None) -> Decimal | None:
    latest = repositories.get_latest_reading(meter_id, line_source_id)
    if latest is None:
        return None
    raw = latest.get("current_value", "")
    if raw in ("", None):
        return None
    try:
        return Decimal(str(raw).replace(",", ""))
    except InvalidOperation:
        return None


def _get_max_produced_unit() -> Decimal:
    raw = getattr(settings, "OCR_MAX_PRODUCED_UNIT_KWH", None)
    if raw in ("", None):
        return DEFAULT_MAX_PRODUCED_KWH
    try:
        return Decimal(str(raw))
    except InvalidOperation:
        return DEFAULT_MAX_PRODUCED_KWH


def _has_conflicting_candidates(
    parsed_value: Decimal,
    candidates: Sequence[Decimal] | None,
) -> bool:
    if not candidates:
        return False
    meaningful = [candidate for candidate in candidates if candidate >= Decimal("1000")]
    if len(meaningful) < 2:
        return False
    for candidate in meaningful:
        if candidate == parsed_value:
            continue
        smaller = min(abs(candidate), abs(parsed_value))
        if smaller == 0:
            continue
        ratio = max(abs(candidate), abs(parsed_value)) / smaller
        if ratio >= Decimal("100"):
            return True
    return False
