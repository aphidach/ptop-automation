from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


@dataclass
class PendingConfirmation:
    meter_id: str
    ocr_value: Optional[Decimal] = None
    manual_value: Optional[Decimal] = None
    ocr_raw_text: str = ""
    image_message_id: str = ""
    batch_id: Optional[str] = None
    created_at: Optional[float] = None


@dataclass
class Session:
    line_source_id: str
    line_user_id: Optional[str] = None
    latest_meter_id: Optional[str] = None
    pending_confirmation: Optional[PendingConfirmation] = None
    batch_id: Optional[str] = None
    processing_image_message_ids: set[str] = field(default_factory=set)
    processed_image_message_ids: set[str] = field(default_factory=set)


class SessionStore(Protocol):
    """Protocol for session storage backends. Swap InMemorySessionStore for Redis/SQLite later."""

    def get(self, source_id: str) -> Optional[Session]: ...
    def set(self, source_id: str, session: Session) -> None: ...
    def delete(self, source_id: str) -> None: ...


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def get(self, source_id: str) -> Optional[Session]:
        return self._sessions.get(source_id)

    def set(self, source_id: str, session: Session) -> None:
        self._sessions[source_id] = session

    def delete(self, source_id: str) -> None:
        self._sessions.pop(source_id, None)


_store: SessionStore = InMemorySessionStore()


def get_or_create_session(source_id: str, user_id: Optional[str] = None) -> Session:
    session = _store.get(source_id)
    if session is None:
        session = Session(line_source_id=source_id, line_user_id=user_id)
        _store.set(source_id, session)
        logger.debug("Created new session for source_id=%s", source_id)
    if user_id and session.line_user_id != user_id:
        session.line_user_id = user_id
    return session


def get_session(source_id: str) -> Optional[Session]:
    return _store.get(source_id)


def set_latest_meter(source_id: str, meter_id: str, user_id: Optional[str] = None) -> None:
    session = get_or_create_session(source_id, user_id)
    session.latest_meter_id = meter_id


def get_latest_meter(source_id: str) -> Optional[str]:
    session = _store.get(source_id)
    return session.latest_meter_id if session else None


def set_pending_confirmation(
    source_id: str,
    meter_id: str,
    ocr_value: Optional[Decimal] = None,
    manual_value: Optional[Decimal] = None,
    ocr_raw_text: str = "",
    image_message_id: str = "",
    batch_id: Optional[str] = None,
    created_at: Optional[float] = None,
) -> None:
    session = get_or_create_session(source_id)
    session.pending_confirmation = PendingConfirmation(
        meter_id=meter_id,
        ocr_value=ocr_value,
        manual_value=manual_value,
        ocr_raw_text=ocr_raw_text,
        image_message_id=image_message_id,
        batch_id=batch_id,
        created_at=created_at,
    )


def get_pending_confirmation(source_id: str) -> Optional[PendingConfirmation]:
    session = _store.get(source_id)
    return session.pending_confirmation if session else None


def clear_pending_confirmation(source_id: str) -> None:
    session = _store.get(source_id)
    if session:
        session.pending_confirmation = None


def start_image_processing(source_id: str, message_id: str) -> bool:
    session = get_or_create_session(source_id)
    if (
        message_id in session.processing_image_message_ids
        or message_id in session.processed_image_message_ids
    ):
        return False
    session.processing_image_message_ids.add(message_id)
    return True


def finish_image_processing(source_id: str, message_id: str) -> None:
    session = get_or_create_session(source_id)
    session.processing_image_message_ids.discard(message_id)
    session.processed_image_message_ids.add(message_id)


def set_batch_id(source_id: str, batch_id: str) -> None:
    session = get_or_create_session(source_id)
    session.batch_id = batch_id


def get_batch_id(source_id: str) -> Optional[str]:
    session = _store.get(source_id)
    return session.batch_id if session else None


def delete_session(source_id: str) -> None:
    _store.delete(source_id)
