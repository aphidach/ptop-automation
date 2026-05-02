import asyncio
import logging
import re

from fastapi import APIRouter, Request, Response
from gspread.exceptions import APIError
from linebot.v3.messaging import (
    AsyncMessagingApi,
    ApiClient,
    Configuration,
    ReplyMessageRequest,
    PushMessageRequest,
    TextMessage,
)
from linebot.v3.messaging.exceptions import ApiException
from linebot.v3.webhook import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError

from app.config import settings
from app.line.parser import (
    METER,
    METER_VALUE,
    OK,
    STATUS,
    HELP,
    CANCEL,
    GEN,
    REPORT,
    UNKNOWN,
    ParsedCommand,
    parse_command,
    is_valid_meter,
)
from app.services.session_service import (
    finish_image_processing,
    get_batch_id as get_session_batch_id,
    get_latest_meter,
    set_latest_meter,
    start_image_processing,
)
from app.services.confirmation_service import (
    create_pending_confirmation,
    build_confirmation_message,
    confirm_pending,
    manual_confirm,
    cancel_pending,
    _ensure_batch_id,
    format_meter_value,
)
from app.services.session_service import (
    get_pending_confirmation as get_session_pending,
)
from app.services.batch_service import build_progress_message
from app.line.client import download_image, ImageDownloadError
from app.ocr.rate_limiter import OcrRateLimiter
from app.ocr.value_parser import parse_meter_value
from app.report.sender import send_report, send_report_if_complete

logger = logging.getLogger(__name__)

router = APIRouter()

_webhook_parser = WebhookParser(channel_secret=settings.LINE_CHANNEL_SECRET)
_messaging_config = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
_messaging_api = AsyncMessagingApi(ApiClient(_messaging_config))
_ocr_limiter = OcrRateLimiter()
_WEEK_REF = re.compile(r"^\d{4}-W\d{2}$", re.IGNORECASE)


def _is_sheets_quota_error(exc: APIError) -> bool:
    return "Quota exceeded" in str(exc) or "[429]" in str(exc)


def _is_invalid_reply_token_error(exc: ApiException) -> bool:
    body = exc.body.decode("utf-8", errors="ignore") if isinstance(exc.body, bytes) else str(exc.body)
    return exc.status == 400 and "Invalid reply token" in body


def _resolve_batch_id(batch_ref: str | None, source_id: str) -> str | None:
    if not batch_ref:
        return get_session_batch_id(source_id)
    if _WEEK_REF.match(batch_ref):
        return f"{batch_ref.upper()}-{source_id}"
    return batch_ref


def _build_status_message(source_id: str) -> str:
    lines: list[str] = []

    meter_id = get_latest_meter(source_id)
    if meter_id:
        lines.append(f"มิเตอร์ปัจจุบัน: {meter_id}")

    pending = get_session_pending(source_id)
    if pending:
        value = pending.manual_value if pending.manual_value is not None else pending.ocr_value
        value_text = format_meter_value(value) if value is not None else "-"
        lines.append(f"รอยืนยัน: {pending.meter_id} = {value_text}")

    batch_id = get_session_batch_id(source_id)
    if batch_id:
        lines.append(build_progress_message(batch_id))

    if not lines:
        return "ยังไม่มีข้อมูลรอบนี้ครับ"

    return "\n".join(lines)


def _build_reply(cmd: ParsedCommand, source_id: str) -> str | None:
    if cmd.type == METER:
        if not is_valid_meter(cmd.meter_id, settings.VALID_METER_IDS):
            valid = ", ".join(settings.VALID_METER_IDS)
            return f'ไม่พบ meter id "{cmd.meter_id}" ครับ\nmeter ที่ใช้ได้: {valid}'
        set_latest_meter(source_id, cmd.meter_id)
        return f"รับทราบ {cmd.meter_id} ส่งรูปได้เลยครับ"

    if cmd.type == METER_VALUE:
        if not is_valid_meter(cmd.meter_id, settings.VALID_METER_IDS):
            valid = ", ".join(settings.VALID_METER_IDS)
            return f'ไม่พบ meter id "{cmd.meter_id}" ครับ\nmeter ที่ใช้ได้: {valid}'
        set_latest_meter(source_id, cmd.meter_id)
        _, reply, batch_id = manual_confirm(source_id, cmd.meter_id, cmd.value)
        if batch_id:
            asyncio.create_task(send_report_if_complete(batch_id, source_id))
        return reply

    if cmd.type == OK:
        _, reply, batch_id = confirm_pending(source_id)
        if batch_id:
            asyncio.create_task(send_report_if_complete(batch_id, source_id))
        return reply

    if cmd.type == STATUS:
        return _build_status_message(source_id)

    if cmd.type == GEN:
        batch_id = _resolve_batch_id(cmd.batch_id, source_id)
        if not batch_id:
            return "ยังไม่มีข้อมูลรอบนี้ครับ"
        asyncio.create_task(send_report(batch_id, source_id))
        return "กำลังส่งรูปรายงานครับ"

    if cmd.type == REPORT:
        batch_id = _resolve_batch_id(cmd.batch_id, source_id)
        if not batch_id:
            return "ยังไม่มีข้อมูลรอบนี้ครับ"
        asyncio.create_task(send_report(batch_id, source_id))
        return "กำลังส่งรูปรายงานครับ"

    if cmd.type == HELP:
        return (
            "📋 คำสั่งที่ใช้ได้:\n"
            "M1 — เลือกมิเตอร์\n"
            "M1 12508 — ใส่ค่าเอง\n"
            "OK — ยืนยันค่า\n"
            "CANCEL — ยกเลิก\n"
            "STATUS — ดูสถานะ\n"
            "GEN [รอบ] — สร้างรูปรายงาน\n"
            "REPORT [รอบ] — ส่งรูปรายงาน\n"
            "HELP — ดูคำสั่ง"
        )

    if cmd.type == CANCEL:
        return cancel_pending(source_id)

    return None


async def _reply_text(reply_token: str, text: str) -> None:
    try:
        _messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)],
            )
        )
    except ApiException as exc:
        if _is_invalid_reply_token_error(exc):
            logger.warning("LINE reply token is invalid or already used")
            return
        logger.exception("Failed to reply via LINE API")
    except Exception:
        logger.exception("Failed to reply via LINE API")


async def _push_text(to: str, text: str) -> None:
    try:
        _messaging_api.push_message(
            PushMessageRequest(to=to, messages=[TextMessage(text=text)])
        )
    except Exception:
        logger.exception("Failed to push message via LINE API")


async def _process_ocr_and_confirm(
    source_id: str, meter_id: str, image_path: str, message_id: str
) -> None:
    try:
        ocr_result = await _ocr_limiter.read_image(image_path)
        if not ocr_result.success:
            await _push_text(
                source_id,
                f"อ่านค่ามิเตอร์ไม่สำเร็จครับ กรุณาพิมพ์ค่าเอง เช่น {meter_id} 12508",
            )
            return

        parsed = parse_meter_value(ocr_result.raw_text)
        if not parsed.success:
            await _push_text(
                source_id,
                f"อ่านค่ามิเตอร์ไม่ได้ครับ กรุณาพิมพ์ค่าเอง เช่น {meter_id} 12508",
            )
            return

        batch_id = _ensure_batch_id(source_id)
        pending = create_pending_confirmation(
            source_id=source_id,
            meter_id=meter_id,
            ocr_value=parsed.value,
            ocr_raw_text=ocr_result.raw_text[:200],
            image_message_id=message_id,
            batch_id=batch_id,
        )
        msg = build_confirmation_message(pending)
        await _push_text(source_id, msg)

    except Exception:
        logger.exception("OCR processing failed for source=%s meter=%s", source_id, meter_id)
        await _push_text(source_id, "เกิดข้อผิดพลาดในการอ่านค่ามิเตอร์ครับ กรุณาลองใหม่")
    finally:
        finish_image_processing(source_id, message_id)


@router.post("/webhook/line")
async def handle_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Line-Signature", "")

    try:
        events = _webhook_parser.parse(body.decode("utf-8"), signature)
    except InvalidSignatureError:
        logger.warning("Invalid LINE signature")
        return Response(status_code=403)

    for event in events:
        event_type = getattr(event, "type", None)
        source = getattr(event, "source", None)
        source_type = getattr(source, "type", None) if source else None
        source_id = (
            getattr(source, "user_id", None)
            or getattr(source, "group_id", None)
            or getattr(source, "room_id", None)
            if source
            else None
        )
        delivery_context = getattr(event, "delivery_context", None)
        is_redelivery = (
            getattr(delivery_context, "is_redelivery", False)
            if delivery_context
            else False
        )
        if is_redelivery:
            logger.info(
                "Skipping redelivered LINE event: id=%s type=%s source_id=%s",
                getattr(event, "webhook_event_id", None),
                event_type,
                source_id,
            )
            continue

        if event_type == "message":
            message = getattr(event, "message", None)
            message_type = getattr(message, "type", None) if message else None
            message_id = getattr(message, "id", None) if message else None
            logger.info(
                "LINE event: type=message, message_type=%s, message_id=%s, source_type=%s, source_id=%s",
                message_type,
                message_id,
                source_type,
                source_id,
            )

            if message_type == "text" and source_id:
                text = getattr(message, "text", "")
                cmd = parse_command(text)
                reply_token = getattr(event, "reply_token", None)

                if cmd.type != UNKNOWN and reply_token:
                    try:
                        reply_text = _build_reply(cmd, source_id)
                    except APIError as exc:
                        if not _is_sheets_quota_error(exc):
                            raise
                        logger.warning("Google Sheets quota exceeded while handling LINE command")
                        reply_text = (
                            "Google Sheets ใช้งานเกินโควตาชั่วคราวครับ "
                            "กรุณาลองใหม่อีกครั้ง หรือพิมพ์ STATUS ภายหลัง"
                        )
                    if reply_text:
                        await _reply_text(reply_token, reply_text)
                elif cmd.type == UNKNOWN and reply_token:
                    await _reply_text(
                        reply_token,
                        "พิมพ์คำสั่งไม่ถูกต้องครับ พิมพ์ HELP เพื่อดูคำสั่งที่ใช้ได้",
                    )

            elif message_type == "image" and source_id and message_id:
                reply_token = getattr(event, "reply_token", None)
                meter_id = get_latest_meter(source_id)

                if not meter_id:
                    if reply_token:
                        await _reply_text(
                            reply_token,
                            "กรุณาพิมพ์ meter id ก่อนส่งรูปครับ เช่น M1",
                        )
                    continue

                if not start_image_processing(source_id, message_id):
                    logger.info("Skipping duplicate image message_id=%s", message_id)
                    continue

                try:
                    image_path = await download_image(message_id)
                    logger.info(
                        "Downloaded image for meter_id=%s: %s", meter_id, image_path
                    )
                    if reply_token:
                        await _reply_text(
                            reply_token,
                            f"รับรูป {meter_id} แล้วครับ กำลังอ่านค่ามิเตอร์...",
                        )
                    asyncio.create_task(
                        _process_ocr_and_confirm(
                            source_id, meter_id, str(image_path), message_id
                        )
                    )
                except ImageDownloadError as exc:
                    finish_image_processing(source_id, message_id)
                    logger.error("Image download failed: %s", exc)
                    if reply_token:
                        await _reply_text(
                            reply_token,
                            "ดาวน์โหลดรูปไม่สำเร็จครับ กรุณาส่งรูปใหม่อีกครั้ง",
                        )
        else:
            logger.info(
                "LINE event: type=%s, source_type=%s, source_id=%s",
                event_type,
                source_type,
                source_id,
            )

    return {"ok": True}
