import logging
import time
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Optional

from app.config import settings
from app.services.batch_service import (
    format_progress_message,
    generate_batch_id,
    get_or_create_batch,
    update_batch_after_reading,
)
from app.services.meter_service import save_reading, validate_reading
from app.services.session_service import (
    PendingConfirmation,
    get_pending_confirmation as get_session_pending_confirmation,
    set_pending_confirmation as set_session_pending_confirmation,
    clear_pending_confirmation as clear_session_pending_confirmation,
    set_batch_id,
    get_batch_id,
)
from app.services.audit_service import (
    log_event,
    EVENT_DUPLICATE_READING,
    EVENT_SHEETS_WRITE_FAILED,
    EVENT_READING_SAVED,
)
from app.sheets.repositories import (
    append_pending_confirmation,
    get_latest_pending_confirmation,
    update_pending_confirmation_status,
)

logger = logging.getLogger(__name__)

PENDING_STATUS_PENDING = "pending"
PENDING_STATUS_CONFIRMED = "confirmed"
PENDING_STATUS_EDITED = "edited"
PENDING_STATUS_CANCELLED = "cancelled"
PENDING_STATUS_EXPIRED = "expired"
PENDING_STATUS_SUPERSEDED = "superseded"


def _iso_from_epoch(timestamp: float) -> str:
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()


def _epoch_from_iso(value) -> Optional[float]:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        pass
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.timestamp()


def _decimal_or_none(value) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        return Decimal(str(value).replace(",", ""))
    except InvalidOperation:
        return None


def _pending_from_row(row: dict) -> PendingConfirmation | None:
    meter_id = str(row.get("meter_id", "")).strip()
    if not meter_id:
        return None
    return PendingConfirmation(
        meter_id=meter_id,
        confirmation_id=str(row.get("confirmation_id", "")).strip() or None,
        ocr_value=_decimal_or_none(row.get("ocr_value")),
        ocr_raw_text=str(row.get("ocr_raw_text", "")),
        image_message_id=str(row.get("image_message_id", "")),
        batch_id=str(row.get("batch_id", "")).strip() or None,
        created_at=_epoch_from_iso(row.get("created_at")),
        expires_at=_epoch_from_iso(row.get("expires_at")),
    )


def _store_pending_in_session(source_id: str, pending: PendingConfirmation) -> None:
    set_session_pending_confirmation(
        source_id=source_id,
        meter_id=pending.meter_id,
        confirmation_id=pending.confirmation_id,
        ocr_value=pending.ocr_value,
        manual_value=pending.manual_value,
        ocr_raw_text=pending.ocr_raw_text,
        image_message_id=pending.image_message_id,
        batch_id=pending.batch_id,
        created_at=pending.created_at,
        expires_at=pending.expires_at,
    )


def _safe_update_pending_status(
    pending: PendingConfirmation,
    status: str,
    source_id: str,
) -> None:
    if not pending.confirmation_id:
        return
    try:
        update_pending_confirmation_status(pending.confirmation_id, status)
    except Exception as exc:
        logger.exception(
            "Failed to update pending confirmation status: confirmation=%s status=%s",
            pending.confirmation_id,
            status,
        )
        log_event(EVENT_SHEETS_WRITE_FAILED, source_id, pending.meter_id, {"error": str(exc)[:200]})


def get_pending_confirmation(source_id: str) -> Optional[PendingConfirmation]:
    pending = get_session_pending_confirmation(source_id)
    if pending:
        return pending

    row = get_latest_pending_confirmation(source_id)
    if not row:
        return None
    pending = _pending_from_row(row)
    if not pending:
        return None
    _store_pending_in_session(source_id, pending)
    return pending


def clear_pending_confirmation(
    source_id: str,
    *,
    status: str = PENDING_STATUS_CANCELLED,
) -> None:
    pending = get_pending_confirmation(source_id)
    if pending:
        _safe_update_pending_status(pending, status, source_id)
    clear_session_pending_confirmation(source_id)


def create_pending_confirmation(
    source_id: str,
    meter_id: str,
    ocr_value: Optional[Decimal] = None,
    ocr_raw_text: str = "",
    image_message_id: str = "",
    batch_id: Optional[str] = None,
    line_user_id: str = "",
) -> PendingConfirmation:
    existing = get_pending_confirmation(source_id)
    if existing:
        _safe_update_pending_status(existing, PENDING_STATUS_SUPERSEDED, source_id)

    return _create_pending_confirmation_record(
        source_id=source_id,
        meter_id=meter_id,
        ocr_value=ocr_value,
        ocr_raw_text=ocr_raw_text,
        image_message_id=image_message_id,
        batch_id=batch_id,
        line_user_id=line_user_id,
    )

def _create_pending_confirmation_record(
    source_id: str,
    meter_id: str,
    ocr_value: Optional[Decimal] = None,
    manual_value: Optional[Decimal] = None,
    ocr_raw_text: str = "",
    image_message_id: str = "",
    batch_id: Optional[str] = None,
    line_user_id: str = "",
) -> PendingConfirmation:
    created_at = time.time()
    expires_at = created_at + settings.CONFIRMATION_EXPIRY_SECONDS
    confirmation_id = f"cnf_{uuid.uuid4().hex[:16]}"
    append_pending_confirmation(
        {
            "confirmation_id": confirmation_id,
            "line_source_id": source_id,
            "line_user_id": line_user_id,
            "meter_id": meter_id,
            "batch_id": batch_id or "",
            "image_message_id": image_message_id,
            "ocr_value": str(ocr_value) if ocr_value is not None else "",
            "ocr_raw_text": ocr_raw_text,
            "status": PENDING_STATUS_PENDING,
            "expires_at": _iso_from_epoch(expires_at),
            "created_at": _iso_from_epoch(created_at),
        }
    )
    set_session_pending_confirmation(
        source_id=source_id,
        meter_id=meter_id,
        confirmation_id=confirmation_id,
        ocr_value=ocr_value,
        manual_value=manual_value,
        ocr_raw_text=ocr_raw_text,
        image_message_id=image_message_id,
        batch_id=batch_id,
        created_at=created_at,
        expires_at=expires_at,
    )
    pending = get_pending_confirmation(source_id)
    assert pending is not None
    logger.info(
        "Created pending confirmation: source=%s meter=%s ocr_value=%s",
        source_id, meter_id, ocr_value,
    )
    return pending

def _confirmation_method(pending: PendingConfirmation) -> str:
    if pending.manual_value is None:
        return "ok"
    if pending.ocr_value is not None and pending.manual_value != pending.ocr_value:
        return "manual_edit"
    return "manual_entry"


def format_meter_value(value: Decimal) -> str:
    text = f"{value:,f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def build_confirmation_message(pending: PendingConfirmation) -> str:
    value = pending.manual_value if pending.manual_value is not None else pending.ocr_value
    value_text = format_meter_value(value) if value is not None else "-"
    return (
        f"มิเตอร์ {pending.meter_id} = {value_text}\n"
        f"พิมพ์ OK เพื่อยืนยัน\n"
        f"หรือพิมพ์ {pending.meter_id} <ค่าที่ถูกต้อง> เพื่อแก้ไข\n"
        f"เช่น {pending.meter_id} 12508 หรือ {pending.meter_id} 135420.05"
    )


def is_expired(pending: PendingConfirmation) -> bool:
    if pending.expires_at is not None:
        return time.time() > pending.expires_at
    if pending.created_at is None:
        return False
    return (time.time() - pending.created_at) > settings.CONFIRMATION_EXPIRY_SECONDS


def _ensure_batch_id(source_id: str) -> str:
    """Get or generate batch_id for this source, persist in session."""
    batch_id = get_batch_id(source_id)
    current_batch_id = generate_batch_id(source_id)
    if batch_id != current_batch_id:
        batch_id = current_batch_id
        set_batch_id(source_id, batch_id)
    get_or_create_batch(batch_id, source_id)
    return batch_id


def ensure_batch_id(source_id: str) -> str:
    return _ensure_batch_id(source_id)


def confirm_pending(
    source_id: str,
    *,
    allow_lower_value: bool = False,
    replace_existing: bool = False,
    line_user_id: str = "",
) -> tuple[Optional[PendingConfirmation], str, Optional[str]]:
    """Handle OK command. Returns (pending, reply_message, batch_id)."""
    pending = get_pending_confirmation(source_id)
    if not pending:
        return None, "ไม่มีค่าที่รอยืนยันครับ", None
    if is_expired(pending):
        clear_pending_confirmation(source_id, status=PENDING_STATUS_EXPIRED)
        return None, "หมดเวลายืนยันแล้ว กรุณาส่งรูปใหม่อีกครั้ง", None
    value = pending.manual_value if pending.manual_value is not None else pending.ocr_value
    if value is None:
        return None, "ไม่มีค่าที่รอยืนยันครับ", None

    batch_id = pending.batch_id or _ensure_batch_id(source_id)
    validation = validate_reading(
        pending.meter_id,
        value,
        batch_id,
        allow_duplicate=replace_existing,
        allow_lower_value=allow_lower_value,
        line_source_id=source_id,
    )
    if not validation.is_valid:
        warning_text = "\n".join(validation.warnings)
        if "ถูกบันทึกไปแล้ว" in warning_text:
            log_event(EVENT_DUPLICATE_READING, source_id, pending.meter_id, {"value": str(value)})
        return pending, f"⚠ ไม่สามารถบันทึกได้:\n{warning_text}", None

    confirmation_method = _confirmation_method(pending)
    try:
        save_reading(
            meter_id=pending.meter_id,
            current_value=value,
            batch_id=batch_id,
            line_source_id=source_id,
            line_user_id=line_user_id,
            ocr_raw_text=pending.ocr_raw_text,
            ocr_value=pending.ocr_value,
            confirmation_method=confirmation_method,
            image_message_id=pending.image_message_id,
            replace_existing=replace_existing,
        )
    except Exception as exc:
        logger.exception("Failed to save reading: meter=%s value=%s", pending.meter_id, value)
        log_event(EVENT_SHEETS_WRITE_FAILED, source_id, pending.meter_id, {"error": str(exc)[:200]})
        return pending, "บันทึกไม่สำเร็จครับ กรุณาลองพิมพ์ OK อีกครั้ง", None
    log_event(EVENT_READING_SAVED, source_id, pending.meter_id, {"value": str(value), "method": confirmation_method})
    _safe_update_pending_status(
        pending,
        PENDING_STATUS_EDITED if confirmation_method == "manual_edit" else PENDING_STATUS_CONFIRMED,
        source_id,
    )
    clear_session_pending_confirmation(source_id)

    progress = update_batch_after_reading(batch_id)
    progress_msg = format_progress_message(progress)
    verb = "แทนที่" if replace_existing else "บันทึก"
    reply = f"{verb} {pending.meter_id} = {format_meter_value(value)} เรียบร้อยครับ\n{progress_msg}"
    return pending, reply, batch_id


def manual_confirm(
    source_id: str,
    meter_id: str,
    value: Decimal,
    line_user_id: str = "",
) -> tuple[Optional[PendingConfirmation], str, Optional[str]]:
    """Handle M1 12508 command. Creates pending with manual value and immediately confirms.
    Returns (pending, reply_message, batch_id).
    """
    batch_id = _ensure_batch_id(source_id)
    pending = get_pending_confirmation(source_id)
    if pending and is_expired(pending):
        clear_pending_confirmation(source_id, status=PENDING_STATUS_EXPIRED)
        pending = None
    if pending and pending.meter_id == meter_id:
        set_session_pending_confirmation(
            source_id=source_id,
            meter_id=meter_id,
            confirmation_id=pending.confirmation_id,
            ocr_value=pending.ocr_value,
            manual_value=value,
            ocr_raw_text=pending.ocr_raw_text,
            image_message_id=pending.image_message_id,
            batch_id=pending.batch_id or batch_id,
            created_at=pending.created_at or time.time(),
            expires_at=pending.expires_at,
        )
    else:
        if pending:
            _safe_update_pending_status(pending, PENDING_STATUS_SUPERSEDED, source_id)
        _create_pending_confirmation_record(
            source_id=source_id,
            meter_id=meter_id,
            ocr_value=value,
            manual_value=value,
            batch_id=batch_id,
            line_user_id=line_user_id,
        )
    logger.info("Manual confirm: source=%s meter=%s value=%s", source_id, meter_id, value)
    return confirm_pending(source_id, line_user_id=line_user_id)


def cancel_pending(source_id: str) -> str:
    """Handle CANCEL command. Returns reply message."""
    pending = get_pending_confirmation(source_id)
    if not pending:
        return "ไม่มีค่าที่รอยืนยันครับ"
    meter_id = pending.meter_id
    clear_pending_confirmation(source_id, status=PENDING_STATUS_CANCELLED)
    logger.info("Cancelled pending: source=%s meter=%s", source_id, meter_id)
    return f"ยกเลิก {meter_id} แล้วครับ"
