import asyncio
import inspect
import logging
import re
import uuid

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
    FlexMessage,
    TextMessage,
)
from linebot.v3.messaging.exceptions import ApiException
from linebot.v3.webhook import WebhookParser
from starlette.requests import ClientDisconnect

from app.config import settings
from app.line.messages import (
    build_batch_complete_card,
    build_confirmation_card,
    build_duplicate_warning_card,
    build_help_flow_response,
    build_help_menu_message,
    build_history_batch_list_message,
    build_history_detail_message,
    build_history_empty_message,
    build_history_menu_message,
    build_history_meter_message,
    build_history_meter_select_message,
    build_history_summary_message,
    build_lower_value_warning,
    build_meter_request_message,
    build_ocr_review_message,
    build_report_import_duplicate_message,
    build_report_import_preview_message,
    build_report_import_prompt_message,
    build_report_import_success_message,
    build_settings_confirm_change_message,
    build_settings_edit_prompt_message,
    build_settings_menu_message,
    build_report_summary_message,
    build_settings_meter_detail_message,
    build_settings_meters_message,
    build_settings_not_admin_message,
    build_settings_permissions_message,
    build_settings_recipients_message,
    build_settings_view_message,
    build_start_collection_card,
    build_status_card,
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
    POSTBACK_HELP_FLOW,
    POSTBACK_HISTORY_BATCH,
    POSTBACK_HISTORY_BATCH_DETAIL,
    POSTBACK_HISTORY_CURRENT,
    POSTBACK_HISTORY_METER,
    POSTBACK_HISTORY_PREVIOUS,
    POSTBACK_HISTORY_SELECT_WEEK,
    POSTBACK_REPLACE_READING,
    POSTBACK_RETAKE_PHOTO,
    POSTBACK_SELECT_METER,
    POSTBACK_SHOW_STATUS,
    POSTBACK_START_COLLECTION,
    POSTBACK_SETTINGS,
    POSTBACK_SETTINGS_CANCEL_CHANGE,
    POSTBACK_SETTINGS_CONFIRM_CHANGE,
    POSTBACK_SETTINGS_CONTACT_ADMIN,
    POSTBACK_CANCEL_IMPORT_REPORT,
    POSTBACK_CONFIRM_IMPORT_REPORT,
    POSTBACK_SETTINGS_EDIT_EXPECTED_COUNT,
    POSTBACK_SETTINGS_EDIT_METER,
    POSTBACK_SETTINGS_EDIT_RATE,
    POSTBACK_SETTINGS_EDIT_REPORT_TITLE,
    POSTBACK_SETTINGS_IMPORT_REPORT,
    POSTBACK_SETTINGS_METER_DETAIL,
    POSTBACK_SETTINGS_METERS,
    POSTBACK_SETTINGS_PERMISSIONS,
    POSTBACK_SETTINGS_RECIPIENTS,
    POSTBACK_SETTINGS_VIEW,
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
from app.services.batch_service import build_progress_message, generate_batch_id, get_batch_progress
from app.services.confirmation_service import (
    _ensure_batch_id,
    clear_pending_confirmation,
    confirm_pending,
    create_pending_confirmation,
    get_pending_confirmation,
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
    REPORT_IMPORT_IDLE,
    REPORT_IMPORT_PROCESSING_OCR,
    REPORT_IMPORT_WAITING_CONFIRMATION,
    REPORT_IMPORT_WAITING_IMAGE,
    clear_collection_meter,
    clear_collection_skip_meters,
    clear_pending_report_import,
    clear_pending_setting_change,
    finish_image_processing,
    get_batch_id as get_session_batch_id,
    get_collection_current_meter,
    get_collection_state,
    get_latest_meter,
    get_pending_report_import,
    get_pending_setting_change,
    get_report_import_state,
    get_settings_input_key,
    is_collection_meter_skipped,
    reset_collection_session,
    reset_report_import_session,
    set_collection_current_meter,
    set_collection_state,
    set_collection_meter_skipped,
    set_batch_id,
    set_pending_report_import,
    set_pending_setting_change,
    set_report_import_state,
    set_settings_input_key,
    start_image_processing,
    set_latest_meter,
)
from app.services import history_service, report_import_service, settings_service
from app.line.client import ImageDownloadError, download_image
from app.report.sender import send_report, send_report_if_complete
from app.ocr.confidence import score_ocr_reading
from app.ocr.google_vision import GoogleVisionOcrClient
from app.ocr.value_parser import parse_meter_value

logger = logging.getLogger(__name__)

router = APIRouter()

_webhook_parser = WebhookParser(channel_secret=settings.LINE_CHANNEL_SECRET)
_messaging_config = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
_messaging_api = AsyncMessagingApi(ApiClient(_messaging_config))
_ocr_client = GoogleVisionOcrClient()
_WEEK_REF = re.compile(r"^\d{4}-W\d{2}$", re.IGNORECASE)
_BARE_VALUE = re.compile(r"^[0-9][0-9,]*(?:\.\d+)?$")
_SHEETS_RETRY_MESSAGE = (
    "Google Sheets ใช้งานเกินโควตาหรือขัดข้องชั่วคราวครับ "
    "กรุณาลองใหม่อีกครั้ง หรือพิมพ์ STATUS ภายหลัง"
)


def _line_source_attr(source, snake_name: str, camel_name: str) -> str | None:
    return getattr(source, snake_name, None) or getattr(source, camel_name, None)


def _line_user_id(source) -> str | None:
    if not source:
        return None
    return _line_source_attr(source, "user_id", "userId")


def _line_chat_id(source) -> str | None:
    if not source:
        return None

    source_type = getattr(source, "type", None)
    if source_type == "group":
        return _line_source_attr(source, "group_id", "groupId")
    if source_type == "room":
        return _line_source_attr(source, "room_id", "roomId")
    if source_type == "user":
        return _line_user_id(source)

    return (
        _line_source_attr(source, "group_id", "groupId")
        or _line_source_attr(source, "room_id", "roomId")
        or _line_user_id(source)
    )


def _is_line_event_allowed(chat_id: str | None, user_id: str | None) -> bool:
    allowed_chat_ids = set(settings.ALLOWED_LINE_SOURCE_IDS)
    allowed_user_ids = set(settings.ALLOWED_LINE_USER_IDS)
    if allowed_user_ids:
        allowed_user_ids.update(settings.ADMIN_LINE_USER_IDS)
        allowed_user_ids.update(settings.OWNER_LINE_USER_IDS)

    if allowed_chat_ids and chat_id not in allowed_chat_ids:
        return False
    if allowed_user_ids and user_id not in allowed_user_ids:
        return False
    return True


def _is_admin_operator(source_id: str, operator_id: str | None = None) -> bool:
    if operator_id and settings_service.is_admin(operator_id):
        return True
    return settings_service.is_admin(source_id)


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


def _restore_collection_from_current_batch(source_id: str) -> str | None:
    batch_id = get_session_batch_id(source_id) or generate_batch_id(source_id)
    progress = get_batch_progress(batch_id)
    if not progress:
        return None

    set_batch_id(source_id, batch_id)
    return _set_next_collection_meter(source_id, batch_id)


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


async def _read_ocr_image(image_path: str):
    return await asyncio.to_thread(_ocr_client.read_image, image_path)


async def _handle_postback_safely(
    source_id: str,
    parsed: ParsedPostback,
    reply_token: str,
    operator_id: str | None = None,
) -> None:
    try:
        await _handle_postback(source_id, parsed, reply_token, operator_id)
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


def _build_status_card_message(source_id: str):
    meter_id = get_collection_current_meter(source_id) or get_latest_meter(source_id)
    pending_text = ""
    pending = get_pending_confirmation(source_id)
    if pending:
        value = pending.manual_value if pending.manual_value is not None else pending.ocr_value
        value_text = format_meter_value(value) if value is not None else "-"
        pending_text = f"{pending.meter_id} = {value_text}"

    batch_id = get_session_batch_id(source_id)
    progress = None
    progress_text = ""
    next_meter = None
    if batch_id:
        try:
            progress = get_batch_progress(batch_id)
            progress_text = build_progress_message(batch_id)
            next_meter = _next_meter_to_capture(source_id, batch_id)
        except Exception:
            logger.exception("Failed to build status card for batch: %s", batch_id)
            progress_text = "ยังดึงความคืบหน้าไม่ได้ครับ"

    return build_status_card(
        meter_id=meter_id,
        pending=pending_text,
        progress_text=progress_text,
        batch_id=batch_id,
        week=progress.week if progress else None,
        confirmed_count=progress.confirmed_meter_count if progress else None,
        total_count=progress.expected_meter_count if progress else None,
        missing_meter_ids=progress.missing_meter_ids if progress else None,
        next_meter=next_meter,
    )


def _build_settings_input_reply(text: str, source_id: str, operator_id: str | None = None):
    key = get_settings_input_key(source_id)
    if not key:
        return None
    if not _is_admin_operator(source_id, operator_id):
        set_settings_input_key(source_id, None)
        return build_settings_not_admin_message()

    valid, value_or_message = settings_service.validate_setting_input(key, text)
    if not valid:
        return value_or_message

    values = settings_service.get_current_settings()
    old_value = values.get(key, "")
    change_id = f"chg_{uuid.uuid4().hex[:12]}"
    set_pending_setting_change(
        source_id=source_id,
        change_id=change_id,
        key=key,
        old_value=old_value,
        new_value=value_or_message,
        label=settings_service.setting_label(key),
        impact=settings_service.setting_impact(key),
    )
    set_settings_input_key(source_id, None)
    change = get_pending_setting_change(source_id)
    return build_settings_confirm_change_message(change)

def _build_settings_edit_prompt(source_id: str, key: str, operator_id: str | None = None):
    if not _is_admin_operator(source_id, operator_id):
        return build_settings_not_admin_message()
    values = settings_service.get_current_settings()
    set_settings_input_key(source_id, key)
    clear_pending_setting_change(source_id)
    return build_settings_edit_prompt_message(key, values.get(key, ""))

async def _reply_history_current(source_id: str, reply_token: str) -> None:
    summary = history_service.get_current_batch_summary(source_id, get_session_batch_id(source_id))
    if not summary:
        await _reply_to(reply_token, build_history_empty_message("ยังไม่มีประวัติการบันทึกในรอบนี้ครับ"))
        return
    if not summary.readings:
        await _reply_to(reply_token, build_history_empty_message("รอบนี้ยังไม่มีค่ามิเตอร์ครับ"))
        return
    await _reply_to(reply_token, build_history_summary_message("ประวัติรอบปัจจุบัน", summary))

async def _reply_history_previous(source_id: str, reply_token: str) -> None:
    summary = history_service.get_previous_batch_summary(source_id, get_session_batch_id(source_id))
    if not summary:
        await _reply_to(reply_token, build_history_empty_message("ยังไม่มีประวัติสัปดาห์ก่อนครับ"))
        return
    await _reply_to(reply_token, build_history_summary_message("ประวัติสัปดาห์ก่อน", summary))

async def _reply_history_detail(batch_id: str | None, source_id: str, reply_token: str) -> None:
    target_batch_id = batch_id or get_session_batch_id(source_id)
    summary = history_service.get_batch_summary(target_batch_id) if target_batch_id else None
    if not summary:
        await _reply_to(reply_token, build_history_empty_message("ไม่พบข้อมูลรอบนี้ครับ"))
        return
    if not summary.readings:
        await _reply_to(reply_token, build_history_empty_message("รอบนี้ยังไม่มีค่ามิเตอร์ครับ"))
        return
    await _reply_to(reply_token, build_history_detail_message(summary))


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


def _build_reply(cmd: ParsedCommand, source_id: str) -> str | TextMessage | FlexMessage | list[str | TextMessage | FlexMessage] | None:
    return _build_text_reply(cmd, source_id)


def _build_text_reply(cmd: ParsedCommand, source_id: str) -> str | TextMessage | FlexMessage | list[str | TextMessage | FlexMessage] | None:
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
        return _build_status_card_message(source_id)

    if cmd.type in (GEN, REPORT):
        batch_id = _resolve_batch_id(cmd.batch_id, source_id)
        if not batch_id:
            return "ยังไม่มีข้อมูลรอบนี้ครับ"
        report_message = build_report_summary_message(batch_id)
        asyncio.create_task(send_report(batch_id, source_id))
        return report_message

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


async def _send_confirm_reading_result(
    source_id: str,
    action: str,
    meter_id: str | None,
) -> None:
    try:
        pending, reply, confirmed_batch_id = confirm_pending(
            source_id,
            allow_lower_value=action == POSTBACK_FORCE_CONFIRM_READING,
        )
        if confirmed_batch_id:
            _after_successful_confirmation(source_id, pending.meter_id if pending else "", confirmed_batch_id)
            progress = get_batch_progress(confirmed_batch_id)
            if progress and not progress.missing_meter_ids:
                set_collection_state(source_id, COLLECTION_REPORTING)
                await _push_to(
                    source_id,
                    build_batch_complete_card(
                        batch_id=confirmed_batch_id,
                        week=progress.week,
                        expected_meter_count=progress.expected_meter_count,
                    ),
                )
                asyncio.create_task(send_report_if_complete(confirmed_batch_id, source_id))
                return

            messages = [reply]
            next_meter = _next_meter_to_capture(source_id, confirmed_batch_id)
            messages.append(_build_status_card_message(source_id))
            if next_meter:
                messages.append(
                    build_meter_request_message(
                        next_meter,
                        meter_ids=settings.VALID_METER_IDS,
                    ),
                )
            await _push_to(source_id, messages)
            return

        if pending is None:
            await _push_to(source_id, reply)
            return

        value = pending.manual_value if pending.manual_value is not None else pending.ocr_value
        warnings = validate_reading(pending.meter_id, value, pending.batch_id or "")
        if "ถูกบันทึกไปแล้ว" in " ".join(warnings.warnings):
            new_value = format_meter_value(value) if value is not None else "-"
            await _push_to(
                source_id,
                build_duplicate_warning_card(
                    pending.meter_id,
                    old_value="มีข้อมูลเดิม",
                    new_value=new_value,
                ),
            )
            return
        if "น้อยกว่า" in " ".join(warnings.warnings):
            current = value or 0
            calc = calculate_reading(pending.meter_id, current)
            await _push_to(
                source_id,
                build_lower_value_warning(
                    pending.meter_id,
                    calc.last_value,
                    current,
                ),
            )
            return
        await _push_to(source_id, reply)
    except APIError as exc:
        log_event(EVENT_SHEETS_WRITE_FAILED, source_id, meter_id or "", {"error": str(exc)[:200]})
        if _is_sheets_quota_error(exc):
            logger.warning("Google Sheets quota exceeded while confirming LINE postback")
        else:
            logger.exception("Google Sheets error while confirming LINE postback")
        await _push_to(source_id, _SHEETS_RETRY_MESSAGE)


async def _handle_postback(
    source_id: str,
    parsed: ParsedPostback,
    reply_token: str,
    operator_id: str | None = None,
) -> None:
    action = parsed.type
    meter_id = parsed.meter_id
    batch_id = _resolve_batch_id(parsed.batch_id, source_id)
    is_admin = _is_admin_operator(source_id, operator_id)

    if action == POSTBACK_START_COLLECTION:
        batch_id = ensure_batch_id(source_id)
        set_collection_state(source_id, COLLECTION_COLLECTING)
        clear_collection_skip_meters(source_id)
        clear_collection_meter(source_id)
        clear_pending_confirmation(source_id)
        next_meter = _set_next_collection_meter(source_id, batch_id)
        progress = get_batch_progress(batch_id)
        expected_meter_count = progress.expected_meter_count if progress else len(settings.VALID_METER_IDS)
        confirmed_meter_count = progress.confirmed_meter_count if progress else 0
        if next_meter:
            await _reply_to(
                reply_token,
                [
                    build_start_collection_card(
                        batch_id=batch_id,
                        week=progress.week if progress else None,
                        expected_meter_count=expected_meter_count,
                        next_meter_id=next_meter,
                        confirmed_meter_count=confirmed_meter_count,
                    ),
                    build_meter_request_message(
                        next_meter,
                        meter_ids=settings.VALID_METER_IDS,
                    ),
                ],
            )
            return
        await _reply_to(
            reply_token,
            [
                build_start_collection_card(
                    batch_id=batch_id,
                    week=progress.week if progress else None,
                    expected_meter_count=expected_meter_count,
                    next_meter_id=None,
                    confirmed_meter_count=confirmed_meter_count or expected_meter_count,
                ),
                f"ครบ {expected_meter_count} เครื่องแล้วครับ",
            ],
        )
        return

    if action == POSTBACK_SHOW_STATUS:
        await _reply_to(reply_token, _build_status_card_message(source_id))
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
                    build_meter_request_message(
                        next_meter,
                        meter_ids=settings.VALID_METER_IDS,
                    ),
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
        await _reply_to(
            reply_token,
            build_meter_request_message(
                meter_id,
                meter_ids=settings.VALID_METER_IDS,
            ),
        )
        return

    if action == POSTBACK_HISTORY:
        await _reply_to(reply_token, build_history_menu_message())
        return

    if action == POSTBACK_HISTORY_CURRENT:
        await _reply_history_current(source_id, reply_token)
        return

    if action == POSTBACK_HISTORY_PREVIOUS:
        await _reply_history_previous(source_id, reply_token)
        return

    if action == POSTBACK_HISTORY_SELECT_WEEK:
        summaries = history_service.get_recent_batch_summaries(source_id)
        await _reply_to(reply_token, build_history_batch_list_message(summaries))
        return

    if action == POSTBACK_HISTORY_BATCH:
        summary = history_service.get_batch_summary(batch_id) if batch_id else None
        if not summary:
            await _reply_to(reply_token, build_history_empty_message("ไม่พบข้อมูลรอบนี้ครับ"))
            return
        await _reply_to(reply_token, build_history_summary_message("ประวัติรอบย้อนหลัง", summary))
        return

    if action == POSTBACK_HISTORY_BATCH_DETAIL:
        await _reply_history_detail(batch_id, source_id, reply_token)
        return

    if action == POSTBACK_HISTORY_METER:
        if not meter_id:
            await _reply_to(reply_token, build_history_meter_select_message(settings.VALID_METER_IDS))
            return
        if not is_valid_meter(meter_id, settings.VALID_METER_IDS):
            await _reply_to(reply_token, build_history_meter_select_message(settings.VALID_METER_IDS))
            return
        readings = history_service.get_meter_history(meter_id, source_id)
        await _reply_to(reply_token, build_history_meter_message(meter_id, readings))
        return

    if action == POSTBACK_SETTINGS:
        await _reply_to(reply_token, build_settings_menu_message(is_admin))
        return

    if action == POSTBACK_SETTINGS_IMPORT_REPORT:
        if not is_admin:
            await _reply_to(reply_token, build_settings_not_admin_message())
            return
        clear_pending_report_import(source_id)
        set_report_import_state(source_id, REPORT_IMPORT_WAITING_IMAGE)
        await _reply_to(reply_token, build_report_import_prompt_message())
        return

    if action == POSTBACK_CONFIRM_IMPORT_REPORT:
        if not is_admin:
            await _reply_to(reply_token, build_settings_not_admin_message())
            return
        pending_import = get_pending_report_import(source_id)
        if not pending_import:
            reset_report_import_session(source_id)
            await _reply_to(reply_token, "ไม่มีรายงานที่รอยืนยันครับ")
            return
        result = report_import_service.confirm_report_import(
            source_id,
            pending_import,
            line_user_id=operator_id or "",
        )
        if result.success:
            set_batch_id(source_id, result.batch_id)
            reset_report_import_session(source_id)
            await _reply_to(reply_token, build_report_import_success_message(result.batch_id, result.week))
            return
        if result.duplicate:
            reset_report_import_session(source_id)
            await _reply_to(reply_token, build_report_import_duplicate_message(result.batch_id, result.week))
            return
        set_report_import_state(source_id, REPORT_IMPORT_WAITING_IMAGE)
        await _reply_to(reply_token, build_report_import_preview_message(pending_import))
        return

    if action == POSTBACK_CANCEL_IMPORT_REPORT:
        if not is_admin:
            await _reply_to(reply_token, build_settings_not_admin_message())
            return
        reset_report_import_session(source_id)
        await _reply_to(reply_token, "ยกเลิกการนำเข้ารายงานเก่าแล้วครับ")
        return

    if action == POSTBACK_SETTINGS_VIEW:
        await _reply_to(
            reply_token,
            build_settings_view_message(
                settings_service.get_current_settings(),
                is_admin,
            ),
        )
        return

    if action == POSTBACK_SETTINGS_METERS:
        await _reply_to(
            reply_token,
            build_settings_meters_message(
                settings_service.get_meter_settings(),
                is_admin,
            ),
        )
        return

    if action == POSTBACK_SETTINGS_METER_DETAIL:
        if not meter_id:
            await _reply_to(reply_token, build_settings_meters_message(settings_service.get_meter_settings(), is_admin))
            return
        meter = settings_service.get_meter_detail(meter_id)
        if not meter:
            await _reply_to(reply_token, "ไม่พบมิเตอร์นี้ครับ")
            return
        await _reply_to(reply_token, build_settings_meter_detail_message(meter, is_admin))
        return

    if action == POSTBACK_SETTINGS_EDIT_RATE:
        await _reply_to(reply_token, _build_settings_edit_prompt(source_id, settings_service.SETTING_DEFAULT_RATE, operator_id))
        return

    if action == POSTBACK_SETTINGS_EDIT_EXPECTED_COUNT:
        await _reply_to(reply_token, _build_settings_edit_prompt(source_id, settings_service.SETTING_EXPECTED_METER_COUNT, operator_id))
        return

    if action == POSTBACK_SETTINGS_EDIT_REPORT_TITLE:
        await _reply_to(reply_token, _build_settings_edit_prompt(source_id, settings_service.SETTING_REPORT_TITLE, operator_id))
        return

    if action == POSTBACK_SETTINGS_EDIT_METER:
        await _reply_to(reply_token, "การแก้ข้อมูลมิเตอร์รายเครื่องจะเพิ่มในเฟสถัดไปครับ")
        return

    if action == POSTBACK_SETTINGS_RECIPIENTS:
        if not is_admin:
            await _reply_to(reply_token, build_settings_not_admin_message())
            return
        await _reply_to(reply_token, build_settings_recipients_message(settings_service.get_current_settings(), True))
        return

    if action == POSTBACK_SETTINGS_PERMISSIONS:
        if not is_admin:
            await _reply_to(reply_token, build_settings_not_admin_message())
            return
        await _reply_to(reply_token, build_settings_permissions_message(True))
        return

    if action == POSTBACK_SETTINGS_CONFIRM_CHANGE:
        if not is_admin:
            await _reply_to(reply_token, build_settings_not_admin_message())
            return
        change = get_pending_setting_change(source_id)
        if not change or (parsed.change_id and parsed.change_id != change.change_id):
            await _reply_to(reply_token, "หมดเวลายืนยันการแก้ไขแล้วครับ")
            return
        settings_service.apply_setting_change(source_id, change.key, change.old_value, change.new_value)
        clear_pending_setting_change(source_id)
        set_settings_input_key(source_id, None)
        await _reply_to(reply_token, build_settings_view_message(settings_service.get_current_settings(), True))
        return

    if action == POSTBACK_SETTINGS_CANCEL_CHANGE:
        clear_pending_setting_change(source_id)
        set_settings_input_key(source_id, None)
        await _reply_to(reply_token, build_settings_menu_message(is_admin))
        return

    if action == POSTBACK_SETTINGS_CONTACT_ADMIN:
        await _reply_to(
            reply_token,
            "กรุณาติดต่อผู้ดูแลระบบใน LINE group นี้ หรือแจ้ง Admin ให้เพิ่ม LINE user id ใน ADMIN_LINE_USER_IDS ครับ",
        )
        return

    if action == POSTBACK_HELP_FLOW:
        await _reply_to(reply_token, build_help_flow_response(parsed.topic))
        return

    if action == POSTBACK_HELP:
        await _reply_to(reply_token, build_help_menu_message())
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
        pending = get_pending_confirmation(source_id)
        target = meter_id or (pending.meter_id if pending else None)
        loading_text = f"กำลังบันทึก {target} ครับ..." if target else "กำลังบันทึกครับ..."
        await _reply_to(reply_token, loading_text)
        await _send_confirm_reading_result(source_id, action, target)
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
        await _reply_to(
            reply_token,
            build_meter_request_message(
                target,
                meter_ids=settings.VALID_METER_IDS,
            ),
        )
        return

    if action == POSTBACK_LATEST_REPORT:
        if not batch_id:
            batch_id = history_service.get_latest_report_batch_id(source_id)
        if not batch_id:
            await _reply_to(reply_token, build_history_empty_message("ยังไม่มีรูปรายงานสำหรับรอบนี้ครับ"))
            return
        await _reply_to(reply_token, build_report_summary_message(batch_id))
        asyncio.create_task(send_report(batch_id, source_id))
        return

    if action == POSTBACK_WEEKLY_SUMMARY:
        if not batch_id:
            batch_id = history_service.get_latest_report_batch_id(source_id)
        if not batch_id:
            await _reply_to(reply_token, "ยังไม่มีข้อมูลรอบนี้ครับ")
            return
        await _reply_to(reply_token, build_report_summary_message(batch_id))
        asyncio.create_task(send_report(batch_id, source_id))
        return

    await _reply_to(reply_token, "ไม่รู้จัก postback action นี้")


async def _process_report_import_image(
    source_id: str,
    image_path: str,
    message_id: str,
) -> None:
    try:
        ocr_result = await _read_ocr_image(image_path)
        if not ocr_result.success:
            log_event(EVENT_OCR_FAILED, source_id, "", {"error": ocr_result.error[:200]})
            set_report_import_state(source_id, REPORT_IMPORT_WAITING_IMAGE)
            await _push_to(source_id, "อ่านรายงานเก่าไม่ได้ครับ กรุณาส่งรูปใหม่อีกครั้ง")
            return

        pending_import = report_import_service.build_report_import_preview(
            source_id,
            ocr_result.raw_text,
            image_message_id=message_id,
        )
        set_pending_report_import(source_id, pending_import)
        if pending_import.duplicate:
            set_report_import_state(source_id, REPORT_IMPORT_IDLE)
        elif report_import_service.can_confirm_import(pending_import):
            set_report_import_state(source_id, REPORT_IMPORT_WAITING_CONFIRMATION)
        else:
            set_report_import_state(source_id, REPORT_IMPORT_WAITING_IMAGE)
        await _push_to(source_id, build_report_import_preview_message(pending_import))
    except Exception:
        logger.exception("Report import OCR failed for source=%s", source_id)
        log_event(EVENT_OCR_FAILED, source_id, "", {"phase": "report_import"})
        set_report_import_state(source_id, REPORT_IMPORT_WAITING_IMAGE)
        await _push_to(source_id, "เกิดข้อผิดพลาดในการอ่านรายงานเก่าครับ กรุณาลองใหม่")
    finally:
        finish_image_processing(source_id, message_id)


async def _process_ocr_and_confirm(
    source_id: str,
    meter_id: str,
    image_path: str,
    message_id: str,
) -> None:
    try:
        ocr_result = await _read_ocr_image(image_path)
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

        confidence = score_ocr_reading(
            meter_id=meter_id,
            parsed_value=parsed.value,
            parse_reason=parsed.reason or "",
            raw_text=ocr_result.raw_text,
            parse_confidence=parsed.confidence,
            unit=parsed.unit,
            candidates=parsed.candidates,
        )
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
        if confidence.is_low:
            set_collection_state(source_id, COLLECTION_WAITING_MANUAL_VALUE)
            await _push_to(
                source_id,
                build_ocr_review_message(
                    meter_id=pending.meter_id,
                    current_value=parsed.value,
                    warnings=confidence.warnings,
                ),
            )
            return

        set_collection_state(source_id, COLLECTION_WAITING_CONFIRMATION)
        await _push_to(
            source_id,
            build_confirmation_card(
                meter_id=pending.meter_id,
                current_value=parsed.value,
                prev_value=calc.last_value,
                produced=calc.produced_unit,
                amount=calc.amount,
                confidence_level=confidence.level,
                confidence_warnings=confidence.warnings,
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
    try:
        body = await request.body()
    except ClientDisconnect:
        logger.info("LINE webhook client disconnected before request body was read")
        return Response(status_code=204)
    signature = request.headers.get("X-Line-Signature", "")
    body_text = body.decode("utf-8")

    try:
        events = _webhook_parser.parse(body_text, signature)
    except InvalidSignatureError:
        logger.warning("Invalid LINE signature")
        return Response(status_code=403)

    for event in events:
        event_type = getattr(event, "type", None)
        source = getattr(event, "source", None)
        source_type = getattr(source, "type", None) if source else None
        source_id = _line_chat_id(source)
        source_user_id = _line_user_id(source)
        delivery_context = getattr(event, "delivery_context", None)
        is_redelivery = (
            getattr(delivery_context, "is_redelivery", False) if delivery_context else False
        )
        if is_redelivery:
            logger.info(
                "Skipping redelivered LINE event: id=%s type=%s line_source_id=%s line_user_id=%s",
                getattr(event, "webhook_event_id", None),
                event_type,
                source_id,
                source_user_id,
            )
            continue

        if not source_id:
            continue

        if not _is_line_event_allowed(source_id, source_user_id):
            logger.info(
                "Skipping unauthorized LINE event: type=%s source_type=%s line_source_id=%s line_user_id=%s",
                event_type,
                source_type,
                source_id,
                source_user_id,
            )
            continue

        if event_type == "postback":
            parsed = parse_postback_action(getattr(getattr(event, "postback", None), "data", ""))
            await _handle_postback_safely(
                source_id,
                parsed,
                getattr(event, "reply_token", ""),
                source_user_id,
            )
            continue

        if event_type != "message":
            logger.info(
                "LINE event: type=%s, source_type=%s, line_source_id=%s, line_user_id=%s",
                event_type,
                source_type,
                source_id,
                source_user_id,
            )
            continue

        message = getattr(event, "message", None)
        message_type = getattr(message, "type", None) if message else None
        message_id = getattr(message, "id", None) if message else None
        logger.info(
            "LINE event: type=message, message_type=%s, message_id=%s, source_type=%s, line_source_id=%s, line_user_id=%s",
            message_type,
            message_id,
            source_type,
            source_id,
            source_user_id,
        )

        reply_token = getattr(event, "reply_token", None)
        collection_state = get_collection_state(source_id)
        if message_type == "text":
            text = getattr(message, "text", "")
            cmd = _coerce_manual_value_command(parse_command(text), text, source_id)
            try:
                settings_reply = (
                    _build_settings_input_reply(text, source_id, source_user_id)
                    if cmd.type == UNKNOWN
                    else None
                )
            except APIError as exc:
                if not _is_sheets_quota_error(exc):
                    log_event(EVENT_SHEETS_WRITE_FAILED, source_id, "", {"error": str(exc)[:200]})
                    raise
                logger.warning("Google Sheets quota exceeded while handling settings input")
                log_event(EVENT_SHEETS_WRITE_FAILED, source_id, "", {"error": "quota_exceeded"})
                settings_reply = _SHEETS_RETRY_MESSAGE
            if settings_reply and reply_token:
                await _reply_to(reply_token, settings_reply)
                continue
            if cmd.type != UNKNOWN and reply_token:
                try:
                    reply_message = _build_text_reply(cmd, source_id)
                except APIError as exc:
                    if not _is_sheets_quota_error(exc):
                        log_event(EVENT_SHEETS_WRITE_FAILED, source_id, "", {"error": str(exc)[:200]})
                        raise
                    logger.warning("Google Sheets quota exceeded while handling LINE command")
                    log_event(EVENT_SHEETS_WRITE_FAILED, source_id, "", {"error": "quota_exceeded"})
                    reply_message = (
                        "Google Sheets ใช้งานเกินโควตาชั่วคราวครับ "
                        "กรุณาลองใหม่อีกครั้ง หรือพิมพ์ STATUS ภายหลัง"
                    )
                if reply_message:
                    await _reply_to(reply_token, reply_message)
            elif cmd.type == UNKNOWN and reply_token:
                await _reply_to(reply_token, "พิมพ์คำสั่งไม่ถูกต้องครับ พิมพ์ HELP เพื่อดูคำสั่งที่ใช้ได้")
            continue

        if message_type == "image":
            report_import_state = get_report_import_state(source_id)
            if report_import_state in (
                REPORT_IMPORT_WAITING_IMAGE,
                REPORT_IMPORT_PROCESSING_OCR,
                REPORT_IMPORT_WAITING_CONFIRMATION,
            ):
                if not _is_admin_operator(source_id, source_user_id):
                    await _reply_to(reply_token, build_settings_not_admin_message())
                    continue
                if report_import_state == REPORT_IMPORT_PROCESSING_OCR:
                    await _reply_to(reply_token, "กำลังอ่านรายงานเก่าอยู่ครับ")
                    continue
                if report_import_state == REPORT_IMPORT_WAITING_CONFIRMATION:
                    pending_import = get_pending_report_import(source_id)
                    if pending_import:
                        await _reply_to(reply_token, build_report_import_preview_message(pending_import))
                    else:
                        set_report_import_state(source_id, REPORT_IMPORT_WAITING_IMAGE)
                        await _reply_to(reply_token, build_report_import_prompt_message())
                    continue

                if not start_image_processing(source_id, message_id):
                    logger.info("Skipping duplicate report import image message_id=%s", message_id)
                    continue

                try:
                    image_path = await download_image(message_id)
                    logger.info("Downloaded report import image: %s", image_path)
                    set_report_import_state(source_id, REPORT_IMPORT_PROCESSING_OCR)
                    if reply_token:
                        await _reply_to(reply_token, "รับรูปรายงานเก่าแล้วครับ กำลังอ่านตาราง...")
                    asyncio.create_task(
                        _process_report_import_image(source_id, str(image_path), message_id)
                    )
                except ImageDownloadError as exc:
                    finish_image_processing(source_id, message_id)
                    set_report_import_state(source_id, REPORT_IMPORT_WAITING_IMAGE)
                    logger.error("Report import image download failed: %s", exc)
                    log_event(
                        EVENT_LINE_DOWNLOAD_FAILED,
                        source_id,
                        "",
                        {"message_id": message_id, "error": str(exc)[:200]},
                    )
                    if reply_token:
                        await _reply_to(
                            reply_token,
                            "ดาวน์โหลดรูปไม่สำเร็จครับ กรุณาส่งรูปรายงานใหม่อีกครั้ง",
                        )
                continue

            meter_id = get_collection_current_meter(source_id) or get_latest_meter(source_id)
            if not meter_id:
                meter_id = _restore_collection_from_current_batch(source_id)
                collection_state = get_collection_state(source_id)

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
