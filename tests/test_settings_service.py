from unittest.mock import patch

from app.services import settings_service


@patch("app.services.settings_service.repositories")
def test_current_settings_falls_back_to_env_defaults(mock_repo):
    mock_repo.get_settings.return_value = {}

    values = settings_service.get_current_settings()

    assert values["expected_meter_count"] == "8"
    assert values["default_rate"] == "4.2"
    assert values["timezone"] == "Asia/Bangkok"


def test_validate_default_rate_requires_positive_number():
    assert settings_service.validate_setting_input("default_rate", "4.5") == (True, "4.5")
    assert settings_service.validate_setting_input("default_rate", "abc")[0] is False
    assert settings_service.validate_setting_input("default_rate", "0")[0] is False


@patch("app.services.settings_service.log_event")
@patch("app.services.settings_service.repositories")
def test_apply_setting_change_updates_sheet_and_logs(mock_repo, mock_log):
    settings_service.apply_setting_change("U1", "default_rate", "4.2", "4.5")

    mock_repo.update_setting.assert_called_once_with("default_rate", "4.5")
    mock_log.assert_called_once()
