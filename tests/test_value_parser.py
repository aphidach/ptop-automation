import pytest
from decimal import Decimal

from app.ocr.value_parser import parse_energy_meter_value, parse_meter_value


class TestParseMeterValue:
    def test_plain_number(self):
        result = parse_meter_value("12500")
        assert result.value == 12500
        assert result.success is True

    def test_comma_separated(self):
        result = parse_meter_value("12,500")
        assert result.value == 12500

    def test_decimal_meter_value(self):
        result = parse_meter_value("Total Energy kWh 135420.05")
        assert result.value == Decimal("135420.05")

    def test_leading_zeros(self):
        result = parse_meter_value("012500")
        assert result.value == 12500

    def test_space_separated(self):
        result = parse_meter_value("12 500")
        assert result.value == 12500

    def test_newline_separated(self):
        result = parse_meter_value("12\n500")
        assert result.value == 12500

    def test_comma_with_leading_zeros(self):
        result = parse_meter_value("012,500")
        assert result.value == 12500

    def test_multiple_candidates_picks_largest(self):
        result = parse_meter_value("M1 12500 Unit 500")
        assert result.value == 12500
        assert 12500 in result.candidates

    def test_no_valid_number(self):
        result = parse_meter_value("hello world")
        assert result.value is None
        assert result.success is False
        assert result.candidates == []

    def test_empty_string(self):
        result = parse_meter_value("")
        assert result.value is None

    def test_whitespace_only(self):
        result = parse_meter_value("   ")
        assert result.value is None

    def test_number_exceeds_max(self):
        result = parse_meter_value("1,234,567")
        assert 1234567 not in result.candidates

    def test_mixed_text_with_date(self):
        result = parse_meter_value("Solar Meter\nReading: 12508\nDate: 2026-05-04")
        assert result.value == 12508

    def test_ocr_markdown_table(self):
        result = parse_meter_value("| Meter | Value |\n| M1 | 12,500 |")
        assert result.value == 12500

    def test_candidates_deduplicated(self):
        result = parse_meter_value("12,500 and 12500")
        assert result.candidates.count(12500) == 1

    def test_zero_value(self):
        result = parse_meter_value("0000")
        assert result.value == 0

    def test_four_digit_value(self):
        result = parse_meter_value("1250")
        assert result.value == 1250

    def test_six_digit_value(self):
        result = parse_meter_value("125000")
        assert result.value == 125000

    def test_seven_digit_exceeds_max(self):
        result = parse_meter_value("1234567")
        assert 1234567 not in result.candidates

    def test_result_preserves_raw_text(self):
        text = "12,500"
        result = parse_meter_value(text)
        assert result.raw_text == text

    def test_number_adjacent_to_text(self):
        result = parse_meter_value("12500kWh")
        assert result.value == 12500

    def test_number_after_label(self):
        result = parse_meter_value("Reading:012500")
        assert result.value == 12500

    def test_thai_text_with_number(self):
        result = parse_meter_value("ค่ามิเตอร์ 12,500 หน่วย")
        assert result.value == 12500

    def test_manual_correction_format(self):
        result = parse_meter_value("M1 12508")
        assert result.value == 12508

    def test_realistic_ocr_output(self):
        text = """Solar Power Meter
Model: SMA-5000
Reading: 12,508 kWh
Date: 04/05/2026"""
        result = parse_meter_value(text)
        assert result.value == 12508


class TestParseEnergyMeterValue:
    def test_e_del_mwh_converts_to_kwh(self):
        result = parse_energy_meter_value("E Del 58.196 MWh")
        assert result.value == Decimal("58196")
        assert result.source_label == "E Del"
        assert result.unit == "MWh"
        assert result.reason == "energy_label_match"

    def test_e_del_second_sample(self):
        result = parse_energy_meter_value("E Del 84.352 MWh")
        assert result.value == Decimal("84352")

    def test_total_energy_kwh_keeps_value(self):
        result = parse_energy_meter_value("Total Energy kWh 135420.05")
        assert result.value == Decimal("135420.05")
        assert result.unit == "kWh"

    def test_total_energy_consumed_keeps_kwh(self):
        result = parse_energy_meter_value("Total Energy Consumed: 250509 kWh")
        assert result.value == Decimal("250509")
        assert result.source_label == "Total Energy Consumed"

    def test_energy_label_beats_power_value(self):
        result = parse_energy_meter_value("Ptot 20.2791 kW\nE Del 58.196 MWh")
        assert result.value == Decimal("58196")

    def test_html_table_energy_value(self):
        result = parse_energy_meter_value("<td>E Del</td><td>60.601</td><td>MWh</td>")
        assert result.value == Decimal("60601")

    def test_ocr_unit_mjh_is_treated_as_mwh(self):
        result = parse_energy_meter_value("<td>E Del</td><td>84.352</td><td>MJh</td>")
        assert result.value == Decimal("84352")
        assert result.unit == "MWh"

    def test_google_vision_muth_unit_is_treated_as_mwh(self):
        result = parse_energy_meter_value("E Del\n58.196\nMuth")
        assert result.value == Decimal("58196")
        assert result.unit == "MWh"

    def test_google_vision_mulh_integer_mwh_keeps_plausible_kwh_value(self):
        result = parse_energy_meter_value("E Del 61270 Mulh")
        assert result.value == Decimal("61270")
        assert result.unit == "MWh"

    def test_google_vision_muh_unit_after_noise_is_treated_as_mwh(self):
        result = parse_energy_meter_value("E Del\nI\n84.352 Muh")
        assert result.value == Decimal("84352")
        assert result.unit == "MWh"

    def test_e_delivered_label_is_supported(self):
        result = parse_energy_meter_value("E Delivered 61.270 MWh")
        assert result.value == Decimal("61270")
        assert result.source_label == "Energy Delivered"

    def test_large_integer_mwh_uses_implied_decimal_when_conversion_exceeds_max(self):
        result = parse_energy_meter_value("Energy Delivered 61270 MWh")
        assert result.value == Decimal("61270")
        assert result.source_label == "Energy Delivered"
        assert result.unit == "MWh"

    def test_e_def_label_ocr_typo_is_supported(self):
        result = parse_energy_meter_value("E Def 58.196 MWh")
        assert result.value == Decimal("58196")
        assert result.source_label == "E Del"

    def test_total_energy_header_uses_larger_kwh_value(self):
        result = parse_energy_meter_value(
            "Comm Frequency Hz Total Energy kWh\n50.0 135420.05"
        )
        assert result.value == Decimal("135420.05")

    def test_google_vision_total_energy_uses_value_after_nearby_kwh_unit(self):
        result = parse_energy_meter_value(
            "Total Energy\n230, 16, 472\nkWh\n50.0 135420.05"
        )
        assert result.value == Decimal("135420.05")
        assert result.source_label == "Total Energy"
        assert result.unit == "kWh"

    def test_total_energy_handles_ocr_split_decimal(self):
        result = parse_energy_meter_value("Total Energy kWh\n50.0 135755. 07")
        assert result.value == Decimal("135755.07")
        assert result.source_label == "Total Energy kWh"
        assert result.unit == "kWh"

    def test_e_del_uses_energy_value_before_label_when_ocr_reorders_lines(self):
        result = parse_energy_meter_value(
            "Ptot 15.2334 k\nkW\n62.683 Muh\nE Del\nU-U\nPQS\n6"
        )
        assert result.value == Decimal("62683")
        assert result.source_label == "E Del"
        assert result.unit == "MWh"

    def test_mpr45s_detail_crop_combines_decimal_tail(self):
        result = parse_energy_meter_value("ENTES\nMPR-45S\n0250509. IkW h")
        assert result.value == Decimal("250509.1")
        assert result.source_label == "MPR-45S energy row"
        assert result.unit == "kWh"

    def test_mpr45s_detail_crop_implies_missing_decimal_tail_low_confidence(self):
        result = parse_energy_meter_value(
            "ENTES\nMPR-45S\n[google_vision_mpr45s_detail]\n0250509 kW h"
        )
        assert result.value == Decimal("250509.1")
        assert result.source_label == "MPR-45S energy row"
        assert result.confidence == "low"
        assert result.reason == "model_specific_implied_decimal_tail"

    def test_mpr45s_spaced_counter_prefix_is_supported(self):
        result = parse_energy_meter_value("ENTES\nMPR-45S\n025 10868kW h")
        assert result.value == Decimal("251086.8")
        assert result.source_label == "MPR-45S energy row"
        assert result.unit == "kWh"

    def test_mpr45s_spaced_counter_with_visible_decimal_is_supported(self):
        result = parse_energy_meter_value("ENTES\nMPR-45S\n025 1086.8kW h")
        assert result.value == Decimal("251086.8")
        assert result.source_label == "MPR-45S energy row"
        assert result.unit == "kWh"

    def test_fallback_still_supports_plain_manual_value(self):
        result = parse_energy_meter_value("M1 12508")
        assert result.value == Decimal("12508")
        assert result.reason == "fallback_generic_number"
