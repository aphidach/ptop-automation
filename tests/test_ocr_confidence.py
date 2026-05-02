from decimal import Decimal
from unittest.mock import patch

from app.ocr.confidence import CONFIDENCE_HIGH, CONFIDENCE_LOW, score_ocr_reading


def test_value_lower_than_last_reading_is_low_confidence():
    with patch(
        "app.ocr.confidence.repositories.get_latest_reading",
        return_value={"current_value": "13000"},
    ):
        result = score_ocr_reading(
            meter_id="M1",
            parsed_value=Decimal("12500"),
            parse_reason="energy_label_match",
            raw_text="E Del 12.5 MWh",
            unit="MWh",
        )

    assert result.level == CONFIDENCE_LOW
    assert result.produced_unit == Decimal("-500")
    assert any("น้อยกว่า" in warning for warning in result.warnings)


def test_huge_jump_from_last_reading_is_low_confidence():
    result = score_ocr_reading(
        meter_id="M1",
        parsed_value=Decimal("50000"),
        parse_reason="energy_label_match",
        raw_text="E Del 50 MWh",
        unit="MWh",
        last_value=Decimal("10000"),
        max_produced_unit=Decimal("1000"),
    )

    assert result.level == CONFIDENCE_LOW
    assert result.produced_unit == Decimal("40000")
    assert any("สูงกว่าเกณฑ์" in warning for warning in result.warnings)


def test_field_aware_parse_with_unit_is_high_confidence_when_plausible():
    result = score_ocr_reading(
        meter_id="M1",
        parsed_value=Decimal("58196"),
        parse_reason="energy_label_match",
        raw_text="E Del 58.196 MWh",
        unit="MWh",
        last_value=Decimal("58000"),
    )

    assert result.level == CONFIDENCE_HIGH
    assert result.reason == "energy_label_unit_plausible"


def test_fallback_generic_parse_is_low_confidence():
    result = score_ocr_reading(
        meter_id="M1",
        parsed_value=Decimal("12508"),
        parse_reason="fallback_generic_number",
        raw_text="M1 12508",
        use_history=False,
    )

    assert result.level == CONFIDENCE_LOW
    assert any("สำรอง" in warning for warning in result.warnings)


def test_impossible_converted_value_is_low_confidence():
    result = score_ocr_reading(
        meter_id="M7",
        parsed_value=Decimal("61270000"),
        parse_reason="energy_label_match",
        raw_text="Energy Delivered 61270 MWh",
        unit="MWh",
        candidates=[Decimal("61270000"), Decimal("61270")],
        use_history=False,
    )

    assert result.level == CONFIDENCE_LOW
    assert any("สูงเกินช่วง" in warning for warning in result.warnings)

def test_conflicting_large_candidates_are_low_confidence():
    result = score_ocr_reading(
        meter_id="M7",
        parsed_value=Decimal("900000"),
        parse_reason="energy_label_match",
        raw_text="Total Energy kWh 900000",
        unit="kWh",
        candidates=[Decimal("900000"), Decimal("5000")],
        use_history=False,
    )

    assert result.level == CONFIDENCE_LOW
    assert any("หลายค่า" in warning for warning in result.warnings)

def test_large_mwh_conversion_is_low_confidence():
    result = score_ocr_reading(
        meter_id="M7",
        parsed_value=Decimal("612700"),
        parse_reason="energy_label_match",
        raw_text="Energy Delivered 612.70 MWh",
        unit="MWh",
        use_history=False,
    )

    assert result.level == CONFIDENCE_LOW
    assert any("จุดทศนิยม" in warning for warning in result.warnings)
