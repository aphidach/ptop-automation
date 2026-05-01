from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


@dataclass
class PendingConfirmation:
    meter_id: str
    ocr_value: Optional[int] = None
    manual_value: Optional[int] = None


@dataclass
class Session:
    line_source_id: str
    line_user_id: Optional[str] = None
    latest_meter_id: Optional[str] = None
    pending_confirmation: Optional[PendingConfirmation] = None
    batch_id: Optional[str] = None


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
    ocr_value: Optional[int] = None,
    manual_value: Optional[int] = None,
) -> None:
    session = get_or_create_session(source_id)
    session.pending_confirmation = PendingConfirmation(
        meter_id=meter_id, ocr_value=ocr_value, manual_value=manual_value,
    )


def get_pending_confirmation(source_id: str) -> Optional[PendingConfirmation]:
    session = _store.get(source_id)
    return session.pending_confirmation if session else None


def clear_pending_confirmation(source_id: str) -> None:
    session = _store.get(source_id)
    if session:
        session.pending_confirmation = None


def set_batch_id(source_id: str, batch_id: str) -> None:
    session = get_or_create_session(source_id)
    session.batch_id = batch_id


def get_batch_id(source_id: str) -> Optional[str]:
    session = _store.get(source_id)
    return session.batch_id if session else None


def delete_session(source_id: str) -> None:
    _store.delete(source_id)
