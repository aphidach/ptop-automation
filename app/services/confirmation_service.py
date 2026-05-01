import logging
import time
from decimal import Decimal
from typing import Optional

from app.config import settings
from app.services.session_service import (
    PendingConfirmation,
    get_pending_confirmation,
    set_pending_confirmation,
    clear_pending_confirmation,
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


def confirm_pending(source_id: str) -> tuple[Optional[PendingConfirmation], str]:
    """Handle OK command. Returns (pending, reply_message)."""
    pending = get_pending_confirmation(source_id)
    if not pending:
        return None, "ไม่มีค่าที่รอยืนยันครับ"
    if is_expired(pending):
        clear_pending_confirmation(source_id)
        return None, "หมดเวลายืนยันแล้ว กรุณาส่งรูปใหม่อีกครั้ง"
    value = pending.manual_value if pending.manual_value is not None else pending.ocr_value
    if value is None:
        return None, "ไม่มีค่าที่รอยืนยันครับ"
    # TODO: Save to Google Sheets (task 11)
    logger.info("Confirmed reading: meter_id=%s value=%s", pending.meter_id, value)
    clear_pending_confirmation(source_id)
    return pending, f"บันทึก {pending.meter_id} = {format_meter_value(value)} เรียบร้อยครับ"


def manual_confirm(source_id: str, meter_id: str, value: Decimal) -> tuple[Optional[PendingConfirmation], str]:
    """Handle M1 12508 command. Creates pending with manual value and immediately confirms."""
    set_pending_confirmation(
        source_id=source_id,
        meter_id=meter_id,
        manual_value=value,
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
