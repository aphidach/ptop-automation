import logging
import time
from decimal import Decimal
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
    get_pending_confirmation,
    set_pending_confirmation,
    clear_pending_confirmation,
    set_batch_id,
    get_batch_id,
)
from app.services.audit_service import (
    log_event,
    EVENT_DUPLICATE_READING,
    EVENT_SHEETS_WRITE_FAILED,
    EVENT_READING_SAVED,
)

logger = logging.getLogger(__name__)


def create_pending_confirmation(
    source_id: str,
    meter_id: str,
    ocr_value: Optional[Decimal] = None,
    ocr_raw_text: str = "",
    image_message_id: str = "",
    batch_id: Optional[str] = None,
) -> PendingConfirmation:
    set_pending_confirmation(
        source_id=source_id,
        meter_id=meter_id,
        ocr_value=ocr_value,
        ocr_raw_text=ocr_raw_text,
        image_message_id=image_message_id,
        batch_id=batch_id,
        created_at=time.time(),
    )
    pending = get_pending_confirmation(source_id)
    logger.info(
        "Created pending confirmation: source=%s meter=%s ocr_value=%s",
        source_id, meter_id, ocr_value,
    )
    return pending


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
    if pending.created_at is None:
        return False
    return (time.time() - pending.created_at) > settings.CONFIRMATION_EXPIRY_SECONDS


def _ensure_batch_id(source_id: str) -> str:
    """Get or generate batch_id for this source, persist in session."""
    batch_id = get_batch_id(source_id)
    if not batch_id:
        batch_id = generate_batch_id(source_id)
        set_batch_id(source_id, batch_id)
    get_or_create_batch(batch_id, source_id)
    return batch_id


def confirm_pending(source_id: str) -> tuple[Optional[PendingConfirmation], str, Optional[str]]:
    """Handle OK command. Returns (pending, reply_message, batch_id)."""
    pending = get_pending_confirmation(source_id)
    if not pending:
        return None, "ไม่มีค่าที่รอยืนยันครับ", None
    if is_expired(pending):
        clear_pending_confirmation(source_id)
        return None, "หมดเวลายืนยันแล้ว กรุณาส่งรูปใหม่อีกครั้ง", None
    value = pending.manual_value if pending.manual_value is not None else pending.ocr_value
    if value is None:
        return None, "ไม่มีค่าที่รอยืนยันครับ", None

    batch_id = pending.batch_id or _ensure_batch_id(source_id)
    validation = validate_reading(pending.meter_id, value, batch_id)
    if not validation.is_valid:
        warning_text = "\n".join(validation.warnings)
        if "ถูกบันทึกไปแล้ว" in warning_text:
            log_event(EVENT_DUPLICATE_READING, source_id, pending.meter_id, {"value": str(value)})
        return pending, f"⚠ ไม่สามารถบันทึกได้:\n{warning_text}", None

    confirmation_method = "manual_edit" if pending.manual_value is not None else "ok"
    try:
        save_reading(
            meter_id=pending.meter_id,
            current_value=value,
            batch_id=batch_id,
            line_source_id=source_id,
            ocr_raw_text=pending.ocr_raw_text,
            ocr_value=pending.ocr_value,
            confirmation_method=confirmation_method,
            image_message_id=pending.image_message_id,
        )
    except Exception as exc:
        logger.exception("Failed to save reading: meter=%s value=%s", pending.meter_id, value)
        log_event(EVENT_SHEETS_WRITE_FAILED, source_id, pending.meter_id, {"error": str(exc)[:200]})
        return pending, "บันทึกไม่สำเร็จครับ กรุณาลองพิมพ์ OK อีกครั้ง", None
    log_event(EVENT_READING_SAVED, source_id, pending.meter_id, {"value": str(value), "method": confirmation_method})
    clear_pending_confirmation(source_id)

    progress = update_batch_after_reading(batch_id)
    progress_msg = format_progress_message(progress)
    reply = f"บันทึก {pending.meter_id} = {format_meter_value(value)} เรียบร้อยครับ\n{progress_msg}"
    return pending, reply, batch_id


def manual_confirm(source_id: str, meter_id: str, value: Decimal) -> tuple[Optional[PendingConfirmation], str, Optional[str]]:
    """Handle M1 12508 command. Creates pending with manual value and immediately confirms.
    Returns (pending, reply_message, batch_id).
    """
    batch_id = _ensure_batch_id(source_id)
    set_pending_confirmation(
        source_id=source_id,
        meter_id=meter_id,
        manual_value=value,
        batch_id=batch_id,
        created_at=time.time(),
    )
    logger.info("Manual confirm: source=%s meter=%s value=%s", source_id, meter_id, value)
    return confirm_pending(source_id)


def cancel_pending(source_id: str) -> str:
    """Handle CANCEL command. Returns reply message."""
    pending = get_pending_confirmation(source_id)
    if not pending:
        return "ไม่มีค่าที่รอยืนยันครับ"
    meter_id = pending.meter_id
    clear_pending_confirmation(source_id)
    logger.info("Cancelled pending: source=%s meter=%s", source_id, meter_id)
    return f"ยกเลิก {meter_id} แล้วครับ"
