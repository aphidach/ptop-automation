import pytest

from app.ocr.value_parser import ParseResult, parse_meter_value


class TestParseMeterValue:
    def test_plain_number(self):
        result = parse_meter_value("12500")
        assert result.value == 12500
        assert result.success is True

    def test_comma_separated(self):
        result = parse_meter_value("12,500")
        assert result.value == 12500

    def test_leading_zeros(self):
        result = parse_meter_value("012500")
        assert result.value == 12500

    def test_space_separated(self):
        result = parse_meter_value("12 500")
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
