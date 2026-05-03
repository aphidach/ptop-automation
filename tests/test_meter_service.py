from decimal import Decimal
from unittest.mock import patch, MagicMock
from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.services.meter_service import (
    ReadingCalculation,
    ValidationResult,
    calculate_reading,
    validate_reading,
    save_reading,
)


@pytest.fixture(autouse=True)
def _mock_repos():
    with patch("app.services.meter_service.repositories") as mock_repos:
        yield mock_repos


class TestCalculateReading:
    def test_basic_calculation(self, _mock_repos):
        _mock_repos.get_latest_reading.return_value = {"current_value": 12000}
        _mock_repos.get_meter_by_id.return_value = {"default_rate": 4.2}

        result = calculate_reading("M1", Decimal(12500))
        assert result.last_value == 12000
        assert result.produced_unit == 500
        assert result.rate == Decimal("4.2")
        assert result.amount == Decimal("2100")

    def test_no_previous_reading(self, _mock_repos):
        _mock_repos.get_latest_reading.return_value = None
        _mock_repos.get_meter_by_id.return_value = {"default_rate": 4.2}

        result = calculate_reading("M1", Decimal(12500))
        assert result.last_value == 0
        assert result.produced_unit == 12500
        assert result.amount == 12500 * Decimal("4.2")

    def test_fallback_default_rate(self, _mock_repos):
        _mock_repos.get_latest_reading.return_value = {"current_value": 1000}
        _mock_repos.get_meter_by_id.return_value = None

        result = calculate_reading("M1", Decimal(1500))
        assert result.rate == Decimal("4.2")

    def test_fallback_default_rate_uses_settings_sheet(self, _mock_repos):
        _mock_repos.get_latest_reading.return_value = {"current_value": 1000}
        _mock_repos.get_meter_by_id.return_value = None
        _mock_repos.get_settings.return_value = {"default_rate": "4.5"}

        result = calculate_reading("M1", Decimal(1500))
        assert result.rate == Decimal("4.5")

    def test_custom_rate(self, _mock_repos):
        _mock_repos.get_latest_reading.return_value = {"current_value": 1000}
        _mock_repos.get_meter_by_id.return_value = {"default_rate": 5.5}

        result = calculate_reading("M1", Decimal(1500))
        assert result.rate == Decimal("5.5")
        assert result.amount == 500 * Decimal("5.5")

    def test_negative_produced_unit(self, _mock_repos):
        _mock_repos.get_latest_reading.return_value = {"current_value": 13000}
        _mock_repos.get_meter_by_id.return_value = {"default_rate": 4.2}

        result = calculate_reading("M1", Decimal(12500))
        assert result.produced_unit == -500
        assert result.amount == -500 * Decimal("4.2")

    def test_decimal_values(self, _mock_repos):
        _mock_repos.get_latest_reading.return_value = {"current_value": "135000.00"}
        _mock_repos.get_meter_by_id.return_value = {"default_rate": 4.2}

        result = calculate_reading("M1", Decimal("135420.05"))
        assert result.last_value == Decimal("135000.00")
        assert result.produced_unit == Decimal("420.05")
        assert result.amount == Decimal("420.05") * Decimal("4.2")


class TestValidateReading:
    def test_valid_reading(self, _mock_repos):
        _mock_repos.get_latest_reading.return_value = {"current_value": 12000}
        _mock_repos.get_readings_by_batch.return_value = []

        result = validate_reading("M1", Decimal(12500), "2026-W19-U1")
        assert result.is_valid is True
        assert result.warnings == []

    def test_value_less_than_last(self, _mock_repos):
        _mock_repos.get_latest_reading.return_value = {"current_value": 13000}
        _mock_repos.get_readings_by_batch.return_value = []

        result = validate_reading("M1", Decimal(12500), "2026-W19-U1")
        assert result.is_valid is False
        assert any("น้อยกว่า" in w for w in result.warnings)

    def test_duplicate_in_batch(self, _mock_repos):
        _mock_repos.get_latest_reading.return_value = {"current_value": 12000}
        _mock_repos.get_readings_by_batch.return_value = [{"meter_id": "M1"}]

        result = validate_reading("M1", Decimal(12500), "2026-W19-U1")
        assert result.is_valid is False
        assert any("ถูกบันทึกไปแล้ว" in w for w in result.warnings)

    def test_multiple_warnings(self, _mock_repos):
        _mock_repos.get_latest_reading.return_value = {"current_value": 13000}
        _mock_repos.get_readings_by_batch.return_value = [{"meter_id": "M1"}]

        result = validate_reading("M1", Decimal(12500), "2026-W19-U1")
        assert result.is_valid is False
        assert len(result.warnings) == 2

    def test_value_equal_to_last(self, _mock_repos):
        _mock_repos.get_latest_reading.return_value = {"current_value": 12500}
        _mock_repos.get_readings_by_batch.return_value = []

        result = validate_reading("M1", Decimal(12500), "2026-W19-U1")
        assert result.is_valid is True


class TestSaveReading:
    def test_save_calls_append_reading(self, _mock_repos):
        _mock_repos.get_latest_reading.return_value = {"current_value": 12000}
        _mock_repos.get_meter_by_id.return_value = {"default_rate": 4.2}

        calc = save_reading(
            meter_id="M1",
            current_value=Decimal(12500),
            batch_id="2026-W19-U1",
            line_source_id="U1",
            confirmation_method="ok",
        )
        assert calc.produced_unit == 500
        assert calc.amount == Decimal("2100")
        _mock_repos.append_reading.assert_called_once()

    def test_save_reading_dict_fields(self, _mock_repos):
        _mock_repos.get_latest_reading.return_value = {"current_value": 12000}
        _mock_repos.get_meter_by_id.return_value = {"default_rate": 4.2}

        save_reading(
            meter_id="M1",
            current_value=Decimal(12500),
            batch_id="2026-W19-U1",
            line_source_id="U1",
            line_user_id="U2",
            ocr_raw_text="12,500",
            ocr_value=Decimal(12500),
            confirmation_method="ok",
            image_message_id="msg1",
        )

        call_args = _mock_repos.append_reading.call_args[0][0]
        assert call_args["meter_id"] == "M1"
        assert call_args["current_value"] == "12500"
        assert call_args["last_value"] == "12000"
        assert call_args["produced_unit"] == "500"
        assert call_args["rate"] == "4.2"
        assert call_args["amount"] == "2100.0"
        assert call_args["batch_id"] == "2026-W19-U1"
        assert call_args["line_source_id"] == "U1"
        assert call_args["line_user_id"] == "U2"
        assert call_args["ocr_raw_text"] == "12,500"
        assert call_args["ocr_value"] == "12500"
        assert call_args["confirmation_method"] == "ok"
        assert call_args["image_message_id"] == "msg1"

    def test_save_reading_uses_configured_timezone_week_and_date(self, _mock_repos):
        _mock_repos.get_latest_reading.return_value = {"current_value": 12000}
        _mock_repos.get_meter_by_id.return_value = {"default_rate": 4.2}
        bangkok_now = datetime(2026, 5, 4, 1, 27, tzinfo=ZoneInfo("Asia/Bangkok"))

        with patch("app.services.meter_service._now", return_value=bangkok_now):
            save_reading(
                meter_id="M1",
                current_value=Decimal(12500),
                batch_id="2026-W19-U1",
                line_source_id="U1",
            )

        call_args = _mock_repos.append_reading.call_args[0][0]
        assert call_args["date"] == "2026-05-04"
        assert call_args["week"] == "2026-W19"

    def test_save_with_manual_edit(self, _mock_repos):
        _mock_repos.get_latest_reading.return_value = {"current_value": 12000}
        _mock_repos.get_meter_by_id.return_value = {"default_rate": 4.2}

        save_reading(
            meter_id="M1",
            current_value=Decimal(12508),
            batch_id="2026-W19-U1",
            line_source_id="U1",
            confirmation_method="manual_edit",
        )

        call_args = _mock_repos.append_reading.call_args[0][0]
        assert call_args["confirmation_method"] == "manual_edit"
        assert call_args["produced_unit"] == "508"
