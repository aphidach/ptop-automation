import time
from decimal import Decimal
from unittest.mock import patch

import pytest

from app.services.confirmation_service import (
    build_confirmation_message,
    cancel_pending,
    confirm_pending,
    create_pending_confirmation,
    get_pending_confirmation as get_hybrid_pending_confirmation,
    is_expired,
    manual_confirm,
)
from app.services.batch_service import BatchProgress
from app.services.session_service import (
    PendingConfirmation,
    clear_pending_confirmation,
    finish_image_processing,
    get_pending_confirmation,
    set_pending_confirmation,
    start_image_processing,
)


@pytest.fixture(autouse=True)
def _clean_sessions():
    from app.services import session_service
    session_service._store = session_service.InMemorySessionStore()
    yield
    session_service._store = session_service.InMemorySessionStore()


@pytest.fixture(autouse=True)
def _mock_meter_service():
    from app.services.meter_service import ValidationResult, ReadingCalculation
    with patch("app.services.confirmation_service.validate_reading") as mock_validate, \
         patch("app.services.confirmation_service.save_reading") as mock_save, \
         patch("app.services.confirmation_service.update_batch_after_reading") as mock_update_batch, \
         patch("app.services.confirmation_service.get_or_create_batch") as mock_get_create_batch, \
         patch("app.services.confirmation_service.get_latest_pending_confirmation", return_value=None) as mock_get_latest_pending, \
         patch("app.services.confirmation_service.append_pending_confirmation") as mock_append_pending, \
         patch("app.services.confirmation_service.update_pending_confirmation_status") as mock_update_pending:
        mock_validate.return_value = ValidationResult(is_valid=True, warnings=[])
        mock_save.return_value = ReadingCalculation(
            last_value=12000, produced_unit=500, rate=Decimal("4.2"), amount=Decimal("2100"),
        )
        mock_update_batch.return_value = BatchProgress(
            batch_id="2026-W19-U1", week="2026-W19", status="collecting",
            expected_meter_count=8, confirmed_meter_count=1, missing_meter_ids=["M2","M3","M4","M5","M6","M7","M8"],
        )
        mock_get_create_batch.return_value = {"batch_id": "2026-W19-U1"}
        yield mock_validate, mock_save, mock_update_batch, mock_get_latest_pending, mock_append_pending, mock_update_pending


class TestCreatePendingConfirmation:
    def test_creates_pending_with_ocr_value(self, _mock_meter_service):
        pending = create_pending_confirmation(
            source_id="U1", meter_id="M1", ocr_value=12500, ocr_raw_text="12,500",
            image_message_id="msg1", batch_id="2026-W19-U1",
        )
        assert pending.meter_id == "M1"
        assert pending.ocr_value == 12500
        assert pending.ocr_raw_text == "12,500"
        assert pending.image_message_id == "msg1"
        assert pending.batch_id == "2026-W19-U1"
        assert pending.created_at is not None
        assert pending.confirmation_id is not None
        assert pending.expires_at is not None
        _mock_meter_service[4].assert_called_once()

    def test_stores_in_session(self):
        create_pending_confirmation(source_id="U1", meter_id="M2", ocr_value=9999)
        pending = get_pending_confirmation("U1")
        assert pending is not None
        assert pending.meter_id == "M2"
        assert pending.ocr_value == 9999

    def test_falls_back_to_sheet_when_session_is_empty(self, _mock_meter_service):
        _mock_meter_service[3].return_value = {
            "confirmation_id": "cnf_sheet",
            "line_source_id": "U1",
            "meter_id": "M4",
            "batch_id": "2026-W19-U1",
            "image_message_id": "msg4",
            "ocr_value": "12500",
            "ocr_raw_text": "12,500",
            "status": "pending",
            "expires_at": "200",
            "created_at": "100",
        }

        pending = get_hybrid_pending_confirmation("U1")

        assert pending is not None
        assert pending.confirmation_id == "cnf_sheet"
        assert pending.meter_id == "M4"
        assert pending.ocr_value == Decimal("12500")
        assert get_pending_confirmation("U1").confirmation_id == "cnf_sheet"

    def test_confirm_after_memory_loss_uses_sheet_fallback(self, _mock_meter_service):
        _mock_meter_service[3].return_value = {
            "confirmation_id": "cnf_sheet",
            "line_source_id": "U1",
            "meter_id": "M1",
            "batch_id": "2026-W19-U1",
            "image_message_id": "msg1",
            "ocr_value": "12500",
            "ocr_raw_text": "12,500",
            "status": "pending",
            "expires_at": str(time.time() + 3600),
            "created_at": str(time.time()),
        }

        pending, reply, batch_id = confirm_pending("U1")

        assert pending is not None
        assert "12,500" in reply
        assert batch_id == "2026-W19-U1"
        _mock_meter_service[1].assert_called_once()
        _mock_meter_service[5].assert_called_with("cnf_sheet", "confirmed")


class TestBuildConfirmationMessage:
    def test_with_ocr_value(self):
        pending = PendingConfirmation(meter_id="M1", ocr_value=12500)
        msg = build_confirmation_message(pending)
        assert "M1" in msg
        assert "12,500" in msg
        assert "OK" in msg
        assert "M1 12508" in msg

    def test_with_manual_value(self):
        pending = PendingConfirmation(meter_id="M3", ocr_value=12000, manual_value=12508)
        msg = build_confirmation_message(pending)
        assert "12,508" in msg


class TestIsExpired:
    def test_not_expired_when_just_created(self):
        pending = PendingConfirmation(meter_id="M1", ocr_value=100, created_at=time.time())
        assert is_expired(pending) is False

    def test_expired_when_old(self):
        pending = PendingConfirmation(
            meter_id="M1", ocr_value=100, created_at=time.time() - 7200,
        )
        assert is_expired(pending) is True

    def test_no_created_at_means_not_expired(self):
        pending = PendingConfirmation(meter_id="M1", ocr_value=100, created_at=None)
        assert is_expired(pending) is False


class TestConfirmPending:
    def test_confirm_ocr_value(self, _mock_meter_service):
        create_pending_confirmation(source_id="U1", meter_id="M1", ocr_value=12500, batch_id="2026-W19-U1")
        pending, reply, batch_id = confirm_pending("U1")
        assert pending is not None
        assert pending.meter_id == "M1"
        assert "12,500" in reply
        assert "บันทึก" in reply
        assert "1/8" in reply
        assert batch_id == "2026-W19-U1"
        _mock_meter_service[5].assert_called_with(pending.confirmation_id, "confirmed")

    def test_confirm_uses_updated_progress_without_reloading(self, _mock_meter_service):
        create_pending_confirmation(source_id="U1", meter_id="M1", ocr_value=12500, batch_id="2026-W19-U1")
        pending, reply, batch_id = confirm_pending("U1")
        assert pending is not None
        assert "1/8" in reply
        assert batch_id == "2026-W19-U1"
        _mock_meter_service[2].assert_called_once_with("2026-W19-U1")

    def test_confirm_clears_pending(self):
        create_pending_confirmation(source_id="U1", meter_id="M1", ocr_value=12500)
        confirm_pending("U1")
        assert get_pending_confirmation("U1") is None

    def test_no_pending_returns_error(self):
        pending, reply, batch_id = confirm_pending("U1")
        assert pending is None
        assert "ไม่มีค่าที่รอยืนยัน" in reply
        assert batch_id is None

    def test_expired_returns_error(self):
        set_pending_confirmation(
            source_id="U1", meter_id="M1", confirmation_id="cnf_old", ocr_value=12500, created_at=time.time() - 7200,
        )
        pending, reply, batch_id = confirm_pending("U1")
        assert pending is None
        assert "หมดเวลายืนยัน" in reply
        assert batch_id is None

    def test_expired_clears_pending(self, _mock_meter_service):
        set_pending_confirmation(
            source_id="U1", meter_id="M1", confirmation_id="cnf_old", ocr_value=12500, created_at=time.time() - 7200,
        )
        confirm_pending("U1")
        assert get_pending_confirmation("U1") is None
        _mock_meter_service[5].assert_called_with("cnf_old", "expired")

    def test_save_failure_does_not_confirm_pending_status(self, _mock_meter_service):
        create_pending_confirmation(source_id="U1", meter_id="M1", ocr_value=12500, batch_id="2026-W19-U1")
        _mock_meter_service[1].side_effect = RuntimeError("write failed")
        _mock_meter_service[5].reset_mock()

        pending, reply, batch_id = confirm_pending("U1")

        assert pending is not None
        assert "บันทึกไม่สำเร็จ" in reply
        assert batch_id is None
        _mock_meter_service[5].assert_not_called()


class TestManualConfirm:
    def test_manual_confirm_immediately_saves(self):
        pending, reply, batch_id = manual_confirm("U1", "M1", 12508)
        assert pending is not None
        assert pending.meter_id == "M1"
        assert "12,508" in reply
        assert "บันทึก" in reply
        assert batch_id is not None

    def test_manual_confirm_clears_pending(self):
        manual_confirm("U1", "M1", 12508)
        assert get_pending_confirmation("U1") is None

    def test_manual_confirm_existing_ocr_marks_edited(self, _mock_meter_service):
        create_pending_confirmation(source_id="U1", meter_id="M1", ocr_value=12500, batch_id="2026-W19-U1")
        _mock_meter_service[5].reset_mock()

        pending, reply, batch_id = manual_confirm("U1", "M1", Decimal("12508"))

        assert pending is not None
        assert "12,508" in reply
        assert batch_id == "2026-W19-U1"
        _mock_meter_service[5].assert_called_with(pending.confirmation_id, "edited")

    def test_manual_confirm_expired_ocr_pending_saves_as_manual_entry(self, _mock_meter_service):
        set_pending_confirmation(
            source_id="U1",
            meter_id="M1",
            confirmation_id="cnf_old",
            ocr_value=Decimal("12500"),
            batch_id="2026-W19-U1",
            created_at=time.time() - 7200,
        )

        pending, reply, batch_id = manual_confirm("U1", "M1", Decimal("12508"))

        assert pending is not None
        assert "12,508" in reply
        assert batch_id is not None
        _mock_meter_service[5].assert_called_with("cnf_old", "expired")


class TestCancelPending:
    def test_cancel_existing(self, _mock_meter_service):
        pending = create_pending_confirmation(source_id="U1", meter_id="M1", ocr_value=12500)
        reply = cancel_pending("U1")
        assert "ยกเลิก" in reply
        assert "M1" in reply
        assert get_pending_confirmation("U1") is None
        _mock_meter_service[5].assert_called_with(pending.confirmation_id, "cancelled")

    def test_cancel_no_pending(self):
        reply = cancel_pending("U1")
        assert "ไม่มีค่าที่รอยืนยัน" in reply


class TestImageProcessingDedupe:
    def test_duplicate_processing_is_rejected(self):
        assert start_image_processing("U1", "msg1") is True
        assert start_image_processing("U1", "msg1") is False

    def test_processed_image_is_rejected(self):
        assert start_image_processing("U1", "msg1") is True
        finish_image_processing("U1", "msg1")
        assert start_image_processing("U1", "msg1") is False
