from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.sheets import repositories

logger = logging.getLogger(__name__)

# Event type constants
EVENT_LINE_DOWNLOAD_FAILED = "line_download_failed"
EVENT_OCR_FAILED = "ocr_failed"
EVENT_OCR_UNREADABLE = "ocr_unreadable"
EVENT_SHEETS_WRITE_FAILED = "sheets_write_failed"
EVENT_DUPLICATE_READING = "duplicate_reading"
EVENT_INVALID_METER = "invalid_meter"
EVENT_READING_SAVED = "reading_saved"
EVENT_BATCH_COMPLETE = "batch_complete"


def log_event(
    event_type: str,
    line_source_id: str = "",
    meter_id: str = "",
    payload: Optional[dict] = None,
) -> None:
    """Log an event to the audit_log Google Sheet tab.

    Silently catches write failures so audit logging never breaks the main flow.
    """
    event_id = f"evt_{uuid.uuid4().hex[:12]}"
    timestamp = datetime.now(timezone.utc).isoformat()
    payload_json = json.dumps(payload, default=str, ensure_ascii=False) if payload else ""

    row = {
        "event_id": event_id,
        "timestamp": timestamp,
        "event_type": event_type,
        "line_source_id": line_source_id,
        "meter_id": meter_id,
        "payload_json": payload_json,
    }

    try:
        repositories.append_audit_log(row)
        logger.info("Audit log: %s source=%s meter=%s", event_type, line_source_id, meter_id)
    except Exception:
        logger.exception(
            "Failed to write audit log: event_type=%s source=%s meter=%s",
            event_type, line_source_id, meter_id,
        )
