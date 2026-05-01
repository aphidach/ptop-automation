import re
from dataclasses import dataclass
from typing import Optional

from app.services.session_service import set_latest_meter, get_latest_meter


METER = "meter"
METER_VALUE = "meter_value"
OK = "ok"
STATUS = "status"
HELP = "help"
CANCEL = "cancel"
UNKNOWN = "unknown"


@dataclass
class ParsedCommand:
    type: str = UNKNOWN
    meter_id: Optional[str] = None
    value: Optional[int] = None
    raw: str = ""


_METER_ONLY = re.compile(r"^([Mm]\d+)$")
_METER_VALUE = re.compile(r"^([Mm]\d+)\s+(\d+)$")


def parse_command(text: str) -> ParsedCommand:
    text = text.strip()
    upper = text.upper()

    if upper == "OK":
        return ParsedCommand(type=OK, raw=text)
    if upper == "STATUS":
        return ParsedCommand(type=STATUS, raw=text)
    if upper == "HELP":
        return ParsedCommand(type=HELP, raw=text)
    if upper == "CANCEL":
        return ParsedCommand(type=CANCEL, raw=text)

    m = _METER_VALUE.match(text)
    if m:
        return ParsedCommand(
            type=METER_VALUE,
            meter_id=m.group(1).upper(),
            value=int(m.group(2)),
            raw=text,
        )

    m = _METER_ONLY.match(text)
    if m:
        return ParsedCommand(type=METER, meter_id=m.group(1).upper(), raw=text)

    return ParsedCommand(type=UNKNOWN, raw=text)


def is_valid_meter(meter_id: str, valid_ids: list[str]) -> bool:
    return meter_id in valid_ids
