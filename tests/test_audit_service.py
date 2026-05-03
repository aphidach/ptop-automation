from unittest.mock import patch

import logging

from app.services.audit_service import EVENT_READING_SAVED, log_event


def test_log_event_writes_to_logger_not_google_sheets(caplog):
    caplog.set_level(logging.INFO, logger="app.services.audit_service")

    with patch("app.sheets.repositories.append_audit_log") as mock_append:
        log_event(EVENT_READING_SAVED, "U1", "M1", {"value": "58196"})

    mock_append.assert_not_called()
    assert "Audit event:" in caplog.text
    assert EVENT_READING_SAVED in caplog.text
