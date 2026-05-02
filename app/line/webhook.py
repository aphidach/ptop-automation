import asyncio
import inspect
import logging
import re

from decimal import Decimal, InvalidOperation
from fastapi import APIRouter, Request, Response
from gspread.exceptions import APIError
from linebot.v3.exceptions import InvalidSignatureError
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

from app.config import settings
from app.line.messages import (
    build_confirmation_card,
    build_lower_value_warning,
    build_meter_request_message,
    build_progress_message as build_progress_text,
    build_start_collection_card,
    build_unreadable_prompt,
)
from app.line.parser import (
    CANCEL,
    GEN,
    HELP,
    METER,
    METER_VALUE,
    OK,
    ParsedCommand,
    ParsedPostback,
    POSTBACK_HISTORY,
    POSTBACK_CANCEL_COLLECTION,
    POSTBACK_CONFIRM_READING,
    POSTBACK_EDIT_READING,
    POSTBACK_FORCE_CONFIRM_READING,
    POSTBACK_HELP,
    POSTBACK_REPLACE_READING,
    POSTBACK_RETAKE_PHOTO,
    POSTBACK_SELECT_METER,
    POSTBACK_SHOW_STATUS,
    POSTBACK_START_COLLECTION,
    POSTBACK_SETTINGS,
    POSTBACK_WEEKLY_SUMMARY,
    POSTBACK_SKIP_METER,
    POSTBACK_LATEST_REPORT,
    REPORT,
    STATUS,
    UNKNOWN,
    parse_command,
    parse_postback_action,
    is_valid_meter,
)
from app.services.audit_service import (
    EVENT_INVALID_METER,
    EVENT_LINE_DOWNLOAD_FAILED,
    EVENT_OCR_FAILED,
    EVENT_OCR_UNREADABLE,
    EVENT_SHEETS_WRITE_FAILED,
    log_event,
)
from app.services.batch_service import build_progress_message, get_batch_progress
from app.services.confirmation_service import (
    _ensure_batch_id,
    confirm_pending,
    create_pending_confirmation,
    ensure_batch_id,
    cancel_pending,
    format_meter_value,
    manual_confirm,
)
from app.services.meter_service import calculate_reading, validate_reading
from app.services.session_service import (
    COLLECTION_COMPLETED,
    COLLECTION_COLLECTING,
    COLLECTION_IDLE,
    COLLECTION_PROCESSING_OCR,
    COLLECTION_WAITING_CONFIRMATION,
    COLLECTION_WAITING_IMAGE,
    COLLECTION_WAITING_MANUAL_VALUE,
    COLLECTION_REPORTING,
    clear_collection_meter,
    clear_collection_skip_meters,
    clear_pending_confirmation,
    finish_image_processing,
    get_batch_id as get_session_batch_id,
    get_collection_current_meter,
    get_collection_state,
    get_latest_meter,
    get_pending_confirmation,
    is_collection_meter_skipped,
    reset_collection_session,
    set_collection_current_meter,
    set_collection_state,
    set_collection_meter_skipped,
    start_image_processing,
    set_latest_meter,
)
from app.line.client import ImageDownloadError, download_image
from app.report.sender import send_report, send_report_if_complete
from app.ocr.rate_limiter import OcrRateLimiter
from app.ocr.value_parser import parse_meter_value

logger = logging.getLogger(__name__)

router = APIRouter()

_webhook_parser = WebhookParser(channel_secret=settings.LINE_CHANNEL_SECRET)
_messaging_config = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
_messaging_api = AsyncMessagingApi(ApiClient(_messaging_config))
_ocr_limiter = OcrRateLimiter()
_WEEK_REF = re.compile(r"^\d{4}-W\d{2}$", re.IGNORECASE)
_BARE_VALUE = re.compile(r"^[0-9][0-9,]*(?:\.\d+)?$")
_SHEETS_RETRY_MESSAGE = (
    "Google Sheets ใช้งานเกินโควตาหรือขัดข้องชั่วคราวครับ "
    "กรุณาลองใหม่อีกครั้ง หรือพิมพ์ STATUS ภายหลัง"
)


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


def _parse_bare_meter_value(text: str) -> Decimal | None:
    candidate = text.strip()
    if not _BARE_VALUE.match(candidate):
        return None
    try:
        return Decimal(candidate.replace(",", ""))
    except InvalidOperation:
        return None


def _coerce_manual_value_command(cmd: ParsedCommand, text: str, source_id: str) -> ParsedCommand:
    if cmd.type != UNKNOWN or get_collection_state(source_id) != COLLECTION_WAITING_MANUAL_VALUE:
        return cmd

    value = _parse_bare_meter_value(text)
    if value is None:
        return cmd

    pending = get_pending_confirmation(source_id)
    meter_id = (
        pending.meter_id if pending else None
    ) or get_collection_current_meter(source_id) or get_latest_meter(source_id)
    if not meter_id:
        return cmd

    return ParsedCommand(type=METER_VALUE, meter_id=meter_id, value=value, raw=text)


def _next_meter_to_capture(source_id: str, batch_id: str | None) -> str | None:
    order = settings.VALID_METER_IDS
    if not order:
        return None
    if not batch_id:
        return order[0]

    progress = get_batch_progress(batch_id)
    missing = set(progress.missing_meter_ids if progress else order)
    for meter in order:
        if meter in missing and not is_collection_meter_skipped(source_id, meter):
            return meter
    return None


async def _reply_to(sender_token: str, messages):
    if not sender_token:
        return
    payload = _normalize_message_payload(messages)

    try:
        response = _messaging_api.reply_message(
            ReplyMessageRequest(reply_token=sender_token, messages=payload)
        )
        await _maybe_await(response)
    except ApiException as exc:
        if _is_invalid_reply_token_error(exc):
            logger.warning("LINE reply token is invalid or already used")
            return
        logger.exception("Failed to reply via LINE API")
    except Exception:
        logger.exception("Failed to reply via LINE API")


async def _push_to(sender_id: str, messages):
    if not sender_id:
        return
    payload = _normalize_message_payload(messages)
    try:
        response = _messaging_api.push_message(PushMessageRequest(to=sender_id, messages=payload))
        await _maybe_await(response)
    except Exception:
        logger.exception("Failed to push via LINE API")


async def _maybe_await(response):
    if inspect.isawaitable(response):
        await response


async def _handle_postback_safely(
    source_id: str,
    parsed: ParsedPostback,
    reply_token: str,
) -> None:
    try:
        await _handle_postback(source_id, parsed, reply_token)
    except APIError as exc:
        log_event(EVENT_SHEETS_WRITE_FAILED, source_id, "", {"error": str(exc)[:200]})
        if _is_sheets_quota_error(exc):
            logger.warning("Google Sheets quota exceeded while handling LINE postback")
        else:
            logger.exception("Google Sheets error while handling LINE postback")
        await _reply_to(reply_token, _SHEETS_RETRY_MESSAGE)


def _normalize_message_payload(messages) -> list:
    if isinstance(messages, str):
        items = [messages]
    elif isinstance(messages, (list, tuple)):
        items = list(messages)
    else:
        items = [messages]

    return [
        TextMessage(text=item) if isinstance(item, str) else item
        for item in items
    ]


def _set_next_collection_meter(source_id: str, batch_id: str | None) -> str | None:
    next_meter = _next_meter_to_capture(source_id, batch_id)
    set_collection_current_meter(source_id, next_meter)
    if next_meter:
        set_latest_meter(source_id, next_meter)
        set_collection_state(source_id, COLLECTION_WAITING_IMAGE)
    else:
        set_collection_state(source_id, COLLECTION_COMPLETED)
    return next_meter


def _build_status_message(source_id: str) -> str:
    lines: list[str] = []
    meter_id = get_collection_current_meter(source_id) or get_latest_meter(source_id)
    if meter_id:
        lines.append(f"มิเตอร์ปัจจุบัน: {meter_id}")

    pending = get_pending_confirmation(source_id)
    if pending:
        value = pending.manual_value if pending.manual_value is not None else pending.ocr_value
        value_text = format_meter_value(value) if value is not None else "-"
        lines.append(f"รอยืนยัน: {pending.meter_id} = {value_text}")

    batch_id = get_session_batch_id(source_id)
    if batch_id:
        progress = None
        try:
            progress = get_batch_progress(batch_id)
        except Exception:
            logger.exception("Failed to get batch progress for status: %s", batch_id)
        if progress:
            remaining = progress.expected_meter_count - progress.confirmed_meter_count
            lines.append(f"ความคืบหน้า: {progress.confirmed_meter_count}/{progress.expected_meter_count} เครื่อง")
            lines.append(f"เหลืออีก {remaining} เครื่อง")
            if progress.missing_meter_ids:
                lines.append(f"รายการที่ยังขาด: {', '.join(progress.missing_meter_ids)}")
            next_meter = _next_meter_to_capture(source_id, batch_id)
            if next_meter:
                lines.append(f"ต่อไป: {next_meter}")
        try:
            lines.append(build_progress_message(batch_id))
        except Exception:
            logger.exception("Failed to build batch progress message for status: %s", batch_id)
            lines.append("ยังดึงความคืบหน้าไม่ได้ครับ")

    if not lines:
        return "ยังไม่มีข้อมูลรอบนี้ครับ"
    return "\n".join(lines)


def _after_successful_confirmation(
    source_id: str,
    pending_meter: str,
    batch_id: str | None,
) -> None:
    if not batch_id:
        return

    _set_next_collection_meter(source_id, batch_id)
    progress = get_batch_progress(batch_id)
    if not progress:
        return

    next_meter = _next_meter_to_capture(source_id, batch_id)
    if not next_meter:
        set_collection_state(source_id, COLLECTION_REPORTING)
        return


def _build_reply(cmd: ParsedCommand, source_id: str) -> str | None:
    return _build_text_reply(cmd, source_id)


def _build_text_reply(cmd: ParsedCommand, source_id: str) -> str | None:
    state = get_collection_state(source_id)
    if cmd.type == METER:
        if not is_valid_meter(cmd.meter_id, settings.VALID_METER_IDS):
            valid = ", ".join(settings.VALID_METER_IDS)
            log_event(EVENT_INVALID_METER, source_id, cmd.meter_id, {"raw": cmd.meter_id})
            return f'ไม่พบ meter id "{cmd.meter_id}" ครับ\nmeter ที่ใช้ได้: {valid}'
        set_latest_meter(source_id, cmd.meter_id)
        set_collection_current_meter(source_id, cmd.meter_id)
        if state in (
            COLLECTION_COLLECTING,
            COLLECTION_WAITING_IMAGE,
            COLLECTION_WAITING_CONFIRMATION,
            COLLECTION_WAITING_MANUAL_VALUE,
        ):
            set_collection_state(source_id, COLLECTION_WAITING_IMAGE)
        return f"รับทราบ {cmd.meter_id} ส่งรูปได้เลยครับ"

    if cmd.type == METER_VALUE:
        if not is_valid_meter(cmd.meter_id, settings.VALID_METER_IDS):
            valid = ", ".join(settings.VALID_METER_IDS)
            log_event(EVENT_INVALID_METER, source_id, cmd.meter_id, {"raw": cmd.meter_id})
            return f'ไม่พบ meter id "{cmd.meter_id}" ครับ\nmeter ที่ใช้ได้: {valid}'
        set_latest_meter(source_id, cmd.meter_id)
        _, reply, batch_id = manual_confirm(source_id, cmd.meter_id, cmd.value)
        _after_successful_confirmation(source_id, cmd.meter_id, batch_id)
        if batch_id:
            asyncio.create_task(send_report_if_complete(batch_id, source_id))
        return reply

    if cmd.type == OK:
        pending, reply, batch_id = confirm_pending(source_id)
        if batch_id and pending:
            _after_successful_confirmation(source_id, pending.meter_id, batch_id)
            asyncio.create_task(send_report_if_complete(batch_id, source_id))
        return reply

    if cmd.type == STATUS:
        return _build_status_message(source_id)

    if cmd.type in (GEN, REPORT):
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


async def _handle_postback(
    source_id: str,
    parsed: ParsedPostback,
    reply_token: str,
) -> None:
    action = parsed.type
    meter_id = parsed.meter_id
    batch_id = _resolve_batch_id(parsed.batch_id, source_id)

    if action == POSTBACK_START_COLLECTION:
        batch_id = ensure_batch_id(source_id)
        set_collection_state(source_id, COLLECTION_COLLECTING)
        clear_collection_skip_meters(source_id)
        clear_collection_meter(source_id)
        clear_pending_confirmation(source_id)
        next_meter = _set_next_collection_meter(source_id, batch_id)
        if next_meter:
            await _reply_to(
                reply_token,
                [build_start_collection_card(), build_meter_request_message(next_meter)],
            )
            return
        await _reply_to(reply_token, [build_start_collection_card(), "ครบ 8 เครื่องแล้วครับ"])
        return

    if action == POSTBACK_SHOW_STATUS:
        await _reply_to(reply_token, _build_status_message(source_id))
        return

    if action == POSTBACK_SKIP_METER:
        target = meter_id or get_collection_current_meter(source_id)
        if not target:
            await _reply_to(reply_token, "ยังไม่ทราบเครื่องที่ต้องข้าม")
            return
        set_collection_meter_skipped(source_id, target)
        next_meter = _set_next_collection_meter(source_id, get_session_batch_id(source_id))
        if next_meter:
            await _reply_to(
                reply_token,
                [
                    f"ข้าม {target} แล้วครับ\nต่อไป: {next_meter}",
                    build_meter_request_message(next_meter),
                ],
            )
            return
        await _reply_to(reply_token, f"ข้าม {target} แล้วครับ")
        return

    if action == POSTBACK_SELECT_METER:
        if not meter_id or not is_valid_meter(meter_id, settings.VALID_METER_IDS):
            await _reply_to(reply_token, "ไม่พบ meter id ที่เลือก")
            return
        set_collection_current_meter(source_id, meter_id)
        set_latest_meter(source_id, meter_id)
        set_collection_state(source_id, COLLECTION_WAITING_IMAGE)
        await _reply_to(reply_token, build_meter_request_message(meter_id))
        return

    if action == POSTBACK_HISTORY:
        await _reply_to(reply_token, "ประวัติกำลังอยู่ในช่วงเตรียมใช้งาน กรุณาส่งคำสั่ง REPORT หรือดูรายงานจากแชต")
        return

    if action == POSTBACK_SETTINGS:
        await _reply_to(reply_token, "ตั้งค่าอยู่ระหว่างอัปเดต กรุณาติดต่อผู้ดูแลระบบหากต้องการแก้ไขข้อมูล")
        return

    if action == POSTBACK_HELP:
        await _reply_to(
            reply_token,
            (
                "ช่วยเหลือ:\n"
                "1) กดบันทึกมิเตอร์เพื่อเริ่มเก็บข้อมูล\n"
                "2) ถ่ายรูปตามลำดับ M1 → M8\n"
                "3) กดยืนยันหลังจาก OCR อ่านค่าเสร็จ\n"
                "หรือพิมพ์คำสั่งเดิมเช่น STATUS / HELP"
            ),
        )
        return

    if action == POSTBACK_CANCEL_COLLECTION:
        reset_collection_session(source_id)
        clear_pending_confirmation(source_id)
        await _reply_to(reply_token, "ยกเลิกการทำงานเดิมแล้ว")
        return

    if action == POSTBACK_REPLACE_READING:
        await _reply_to(reply_token, "การแทนที่ข้อมูลจะเพิ่มในเวอร์ชันถัดไปครับ")
        return

    if action in (POSTBACK_CONFIRM_READING, POSTBACK_FORCE_CONFIRM_READING):
        pending, reply, confirmed_batch_id = confirm_pending(
            source_id,
            allow_lower_value=action == POSTBACK_FORCE_CONFIRM_READING,
        )
        if confirmed_batch_id:
            _after_successful_confirmation(source_id, pending.meter_id if pending else "", confirmed_batch_id)
            progress = get_batch_progress(confirmed_batch_id)
            if progress and not progress.missing_meter_ids:
                set_collection_state(source_id, COLLECTION_REPORTING)
                await _reply_to(reply_token, "บันทึกครบ 8 เครื่องแล้วครับ\nกำลังสร้างรายงาน")
                asyncio.create_task(send_report_if_complete(confirmed_batch_id, source_id))
                return

            messages = [
                reply,
                build_progress_text(
                    pending.meter_id if pending else meter_id or "",
                    progress.confirmed_meter_count if progress else 0,
                    progress.expected_meter_count if progress else settings.EXPECTED_METER_COUNT,
                    _next_meter_to_capture(source_id, confirmed_batch_id),
                ),
            ]
            next_meter = _next_meter_to_capture(source_id, confirmed_batch_id)
            if next_meter:
                messages.append(build_meter_request_message(next_meter))
            await _reply_to(reply_token, messages)
            return

        if pending is None:
            await _reply_to(reply_token, reply)
            return

        value = pending.manual_value if pending.manual_value is not None else pending.ocr_value
        warnings = validate_reading(pending.meter_id, value, pending.batch_id or "")
        if "ถูกบันทึกไปแล้ว" in " ".join(warnings.warnings):
            await _reply_to(reply_token, "รอบนี้มีค่าเดิมอยู่แล้วครับ\nการแทนที่ข้อมูลจะเพิ่มในเวอร์ชันถัดไป")
            return
        if "น้อยกว่า" in " ".join(warnings.warnings):
            current = value or 0
            calc = calculate_reading(pending.meter_id, current)
            await _reply_to(
                reply_token,
                build_lower_value_warning(
                    pending.meter_id,
                    calc.last_value,
                    current,
                ),
            )
            return
        await _reply_to(reply_token, reply)
        return

    if action == POSTBACK_EDIT_READING:
        target = meter_id or get_collection_current_meter(source_id)
        if not target:
            await _reply_to(reply_token, "ยังไม่ได้เลือกเครื่องครับ พิมพ์ M1 12508 เพื่อแก้ไข")
            return
        set_collection_state(source_id, COLLECTION_WAITING_MANUAL_VALUE)
        await _reply_to(
            reply_token,
            f"แก้ไขค่า {target} โดยพิมพ์ {target} <ค่าที่ถูกต้อง> หรือส่งค่าทันที",
        )
        return

    if action == POSTBACK_RETAKE_PHOTO:
        target = meter_id or get_collection_current_meter(source_id)
        if not target:
            await _reply_to(reply_token, "ยังไม่ทราบเครื่องที่ต้องถ่ายใหม่")
            return
        clear_pending_confirmation(source_id)
        set_collection_state(source_id, COLLECTION_WAITING_IMAGE)
        await _reply_to(reply_token, build_meter_request_message(target))
        return

    if action == POSTBACK_LATEST_REPORT:
        if not batch_id:
            await _reply_to(reply_token, "ยังไม่มีข้อมูลรอบนี้ครับ")
            return
        asyncio.create_task(send_report(batch_id, source_id))
        await _reply_to(reply_token, "กำลังส่งรายงานล่าสุดครับ")
        return

    if action == POSTBACK_WEEKLY_SUMMARY:
        if not batch_id:
            await _reply_to(reply_token, "ยังไม่มีข้อมูลรอบนี้ครับ")
            return
        asyncio.create_task(send_report(batch_id, source_id))
        await _reply_to(reply_token, "กำลังส่งสรุปรายสัปดาห์ครับ")
        return

    await _reply_to(reply_token, "ไม่รู้จัก postback action นี้")


async def _process_ocr_and_confirm(
    source_id: str,
    meter_id: str,
    image_path: str,
    message_id: str,
) -> None:
    try:
        ocr_result = await _ocr_limiter.read_image(image_path)
        if not ocr_result.success:
            log_event(EVENT_OCR_FAILED, source_id, meter_id, {"error": ocr_result.error[:200]})
            set_collection_state(source_id, COLLECTION_WAITING_MANUAL_VALUE)
            await _push_to(source_id, build_unreadable_prompt(meter_id))
            return

        parsed = parse_meter_value(ocr_result.raw_text)
        if not parsed.success:
            log_event(EVENT_OCR_UNREADABLE, source_id, meter_id, {"raw_text": ocr_result.raw_text[:200]})
            set_collection_state(source_id, COLLECTION_WAITING_MANUAL_VALUE)
            await _push_to(source_id, build_unreadable_prompt(meter_id))
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
        calc = calculate_reading(meter_id, parsed.value)
        set_collection_state(source_id, COLLECTION_WAITING_CONFIRMATION)
        await _push_to(
            source_id,
            build_confirmation_card(
                meter_id=pending.meter_id,
                current_value=parsed.value,
                prev_value=calc.last_value,
                produced=calc.produced_unit,
                amount=calc.amount,
            ),
        )
    except Exception:
        logger.exception("OCR processing failed for source=%s meter=%s", source_id, meter_id)
        log_event(EVENT_OCR_FAILED, source_id, meter_id, {"phase": "ocr_processing"})
        set_collection_state(source_id, COLLECTION_WAITING_MANUAL_VALUE)
        await _push_to(source_id, "เกิดข้อผิดพลาดในการอ่านค่ามิเตอร์ครับ กรุณาลองใหม่")
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
            getattr(delivery_context, "is_redelivery", False) if delivery_context else False
        )
        if is_redelivery:
            logger.info(
                "Skipping redelivered LINE event: id=%s type=%s source_id=%s",
                getattr(event, "webhook_event_id", None),
                event_type,
                source_id,
            )
            continue

        if event_type == "postback":
            if not source_id:
                continue
            parsed = parse_postback_action(getattr(getattr(event, "postback", None), "data", ""))
            await _handle_postback_safely(source_id, parsed, getattr(event, "reply_token", ""))
            continue

        if event_type != "message":
            logger.info(
                "LINE event: type=%s, source_type=%s, source_id=%s",
                event_type,
                source_type,
                source_id,
            )
            continue

        if not source_id:
            continue

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

        reply_token = getattr(event, "reply_token", None)
        collection_state = get_collection_state(source_id)
        if message_type == "text":
            text = getattr(message, "text", "")
            cmd = _coerce_manual_value_command(parse_command(text), text, source_id)
            if cmd.type != UNKNOWN and reply_token:
                try:
                    reply_text = _build_text_reply(cmd, source_id)
                except APIError as exc:
                    if not _is_sheets_quota_error(exc):
                        log_event(EVENT_SHEETS_WRITE_FAILED, source_id, "", {"error": str(exc)[:200]})
                        raise
                    logger.warning("Google Sheets quota exceeded while handling LINE command")
                    log_event(EVENT_SHEETS_WRITE_FAILED, source_id, "", {"error": "quota_exceeded"})
                    reply_text = (
                        "Google Sheets ใช้งานเกินโควตาชั่วคราวครับ "
                        "กรุณาลองใหม่อีกครั้ง หรือพิมพ์ STATUS ภายหลัง"
                    )
                if reply_text:
                    await _reply_to(reply_token, reply_text)
            elif cmd.type == UNKNOWN and reply_token:
                await _reply_to(reply_token, "พิมพ์คำสั่งไม่ถูกต้องครับ พิมพ์ HELP เพื่อดูคำสั่งที่ใช้ได้")
            continue

        if message_type == "image":
            meter_id = get_collection_current_meter(source_id) or get_latest_meter(source_id)
            if collection_state in (COLLECTION_WAITING_CONFIRMATION, COLLECTION_PROCESSING_OCR):
                if meter_id:
                    await _reply_to(reply_token, build_unreadable_prompt(meter_id))
                else:
                    await _reply_to(reply_token, "ยังไม่ทราบเครื่องที่จะบันทึก กรุณาเลือกก่อน")
                continue

            if not meter_id:
                if collection_state in (COLLECTION_IDLE, COLLECTION_COMPLETED):
                    await _reply_to(reply_token, "กรุณาพิมพ์ meter id ก่อนส่งรูปครับ เช่น M1")
                    continue
                if collection_state == COLLECTION_COLLECTING:
                    meter_id = _next_meter_to_capture(source_id, get_session_batch_id(source_id))
                    if meter_id:
                        set_collection_current_meter(source_id, meter_id)
                        set_latest_meter(source_id, meter_id)

            if not meter_id:
                await _reply_to(reply_token, "กรุณาเริ่มรอบบันทึกก่อนส่งรูป")
                continue

            if not start_image_processing(source_id, message_id):
                logger.info("Skipping duplicate image message_id=%s", message_id)
                continue

            try:
                image_path = await download_image(message_id)
                logger.info("Downloaded image for meter_id=%s: %s", meter_id, image_path)
                set_collection_state(source_id, COLLECTION_PROCESSING_OCR)
                if reply_token:
                    await _reply_to(
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
                log_event(
                    EVENT_LINE_DOWNLOAD_FAILED,
                    source_id,
                    meter_id,
                    {"message_id": message_id, "error": str(exc)[:200]},
                )
                if reply_token:
                    await _reply_to(
                        reply_token,
                        "ดาวน์โหลดรูปไม่สำเร็จครับ กรุณาส่งรูปใหม่อีกครั้ง",
                    )
            continue

        logger.info(
            "Unsupported LINE message type=%s source_type=%s source_id=%s",
            message_type,
            source_type,
            source_id,
        )

    return {"ok": True}
