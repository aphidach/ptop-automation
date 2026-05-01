import logging

from fastapi import APIRouter, Request, Response
from linebot.v3.messaging import (
    AsyncMessagingApi,
    Configuration,
    ReplyMessageRequest,
    TextMessage,
)
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
    UNKNOWN,
    ParsedCommand,
    parse_command,
    is_valid_meter,
    set_latest_meter,
)

logger = logging.getLogger(__name__)

router = APIRouter()

_webhook_parser = WebhookParser(channel_secret=settings.LINE_CHANNEL_SECRET)
_messaging_config = Configuration(access_token=settings.LINE_CHANNEL_ACCESS_TOKEN)
_messaging_api = AsyncMessagingApi(_messaging_config)


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
        return f"รับทราบ {cmd.meter_id} = {cmd.value:,}"

    if cmd.type == OK:
        return "ยืนยันสำเร็จครับ"

    if cmd.type == STATUS:
        return "ยังไม่มีข้อมูลรอบนี้ครับ"

    if cmd.type == HELP:
        return (
            "คำสั่งที่ใช้ได้:\n"
            "M1 — เลือก meter\n"
            "M1 12508 — ใส่ค่าเอง\n"
            "OK — ยืนยันค่า\n"
            "STATUS — ดูความคืบหน้า\n"
            "CANCEL — ยกเลิก\n"
            "HELP — ดูคำสั่ง"
        )

    if cmd.type == CANCEL:
        return "ยกเลิกแล้วครับ"

    return None


async def _reply_text(reply_token: str, text: str) -> None:
    try:
        await _messaging_api.reply_message(
            ReplyMessageRequest(
                reply_token=reply_token,
                messages=[TextMessage(text=text)],
            )
        )
    except Exception:
        logger.exception("Failed to reply via LINE API")


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
                    reply_text = _build_reply(cmd, source_id)
                    if reply_text:
                        await _reply_text(reply_token, reply_text)
                elif cmd.type == UNKNOWN and reply_token:
                    await _reply_text(
                        reply_token,
                        "พิมพ์คำสั่งไม่ถูกต้องครับ พิมพ์ HELP เพื่อดูคำสั่งที่ใช้ได้",
                    )
        else:
            logger.info(
                "LINE event: type=%s, source_type=%s, source_id=%s",
                event_type,
                source_type,
                source_id,
            )

    return {"ok": True}
