from __future__ import annotations

import logging
import sqlite3
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import settings
from app.storage.schema import TAB_HEADERS

logger = logging.getLogger(__name__)


class SQLiteClient:
    def __init__(self, db_path: str | None = None) -> None:
        self._db_path = db_path
        self._is_setup = False

    @property
    def db_path(self) -> Path:
        return Path(self._db_path or settings.SQLITE_DB_PATH)

    def connect(self) -> sqlite3.Connection:
        path = self.db_path
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 5000")
        conn.execute("PRAGMA foreign_keys = ON")
        if not self._is_setup:
            self.setup(conn)
        return conn

    def setup(self, conn: sqlite3.Connection | None = None) -> None:
        owns_connection = conn is None
        if conn is None:
            path = self.db_path
            path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA busy_timeout = 5000")
            conn.execute("PRAGMA foreign_keys = ON")

        try:
            for table, headers in TAB_HEADERS.items():
                columns = ", ".join(f"{column} TEXT" for column in headers)
                conn.execute(f"CREATE TABLE IF NOT EXISTS {table} ({columns})")
            self._create_sync_outbox(conn)
            self._create_indexes(conn)
            conn.commit()
            self._is_setup = True
        finally:
            if owns_connection:
                conn.close()

    def read_all(self, tab_name: str) -> list[dict]:
        headers = self._headers(tab_name)
        columns = ", ".join(headers)
        conn = self.connect()
        try:
            rows = conn.execute(f"SELECT {columns} FROM {tab_name} ORDER BY rowid").fetchall()
        finally:
            conn.close()
        logger.info("Read %d rows from SQLite table '%s'", len(rows), tab_name)
        return [self._row_to_dict(row, headers) for row in rows]

    def find_rows(self, tab_name: str, column: str, value: str) -> list[dict]:
        headers = self._headers(tab_name)
        if column not in headers:
            raise ValueError(f"Unknown column '{column}' for table '{tab_name}'")
        columns = ", ".join(headers)
        conn = self.connect()
        try:
            rows = conn.execute(
                f"SELECT {columns} FROM {tab_name} WHERE {column} = ? ORDER BY rowid",
                (str(value),),
            ).fetchall()
        finally:
            conn.close()
        return [self._row_to_dict(row, headers) for row in rows]

    def append_row(self, tab_name: str, row: dict) -> None:
        headers = self._headers(tab_name)
        placeholders = ", ".join("?" for _ in headers)
        columns = ", ".join(headers)
        values = [self._to_text(row.get(header, "")) for header in headers]
        conn = self.connect()
        try:
            conn.execute(
                f"INSERT INTO {tab_name} ({columns}) VALUES ({placeholders})",
                values,
            )
            conn.commit()
        finally:
            conn.close()
        logger.info("Appended row to SQLite table '%s'", tab_name)

    def replace_all(self, tab_name: str, rows: list[dict]) -> None:
        self._headers(tab_name)
        conn = self.connect()
        try:
            conn.execute(f"DELETE FROM {tab_name}")
            conn.commit()
        finally:
            conn.close()
        for row in rows:
            self.append_row(tab_name, row)
        logger.info("Replaced SQLite table '%s' with %d row(s)", tab_name, len(rows))

    def update_rows(self, tab_name: str, match_column: str, match_value: str, values: dict) -> int:
        headers = self._headers(tab_name)
        if match_column not in headers:
            raise ValueError(f"Unknown column '{match_column}' for table '{tab_name}'")
        updates = {key: value for key, value in values.items() if key in headers}
        if not updates:
            return 0
        set_clause = ", ".join(f"{key} = ?" for key in updates)
        params = [self._to_text(value) for value in updates.values()]
        params.append(str(match_value))
        conn = self.connect()
        try:
            cursor = conn.execute(
                f"UPDATE {tab_name} SET {set_clause} WHERE {match_column} = ?",
                params,
            )
            conn.commit()
            return cursor.rowcount
        finally:
            conn.close()

    def enqueue_outbox(
        self,
        table_name: str,
        row_key: str,
        payload: dict,
        operation: str = "upsert",
    ) -> None:
        if not row_key:
            logger.warning("Skipping sync outbox enqueue for %s with empty row key", table_name)
            return

        now = self._now()
        payload_json = json.dumps(payload, ensure_ascii=False, default=str)
        conn = self.connect()
        try:
            conn.execute(
                """
                INSERT INTO sync_outbox (
                    table_name, row_key, payload_json, operation, status,
                    attempt_count, last_error, created_at, updated_at, synced_at
                ) VALUES (?, ?, ?, ?, 'pending', 0, '', ?, ?, '')
                ON CONFLICT(table_name, row_key) DO UPDATE SET
                    payload_json = excluded.payload_json,
                    operation = excluded.operation,
                    status = 'pending',
                    attempt_count = 0,
                    last_error = '',
                    updated_at = excluded.updated_at,
                    synced_at = ''
                """,
                (table_name, row_key, payload_json, operation, now, now),
            )
            conn.commit()
        finally:
            conn.close()

    def fetch_outbox(self, limit: int) -> list[dict]:
        conn = self.connect()
        try:
            rows = conn.execute(
                """
                SELECT table_name, row_key, payload_json, operation, status,
                       attempt_count, last_error, created_at, updated_at, synced_at
                FROM sync_outbox
                WHERE status IN ('pending', 'failed')
                ORDER BY created_at, updated_at
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        finally:
            conn.close()
        return [dict(row) for row in rows]

    def mark_outbox_synced(self, table_name: str, row_key: str) -> None:
        now = self._now()
        conn = self.connect()
        try:
            conn.execute(
                """
                UPDATE sync_outbox
                SET status = 'synced', last_error = '', updated_at = ?, synced_at = ?
                WHERE table_name = ? AND row_key = ?
                """,
                (now, now, table_name, row_key),
            )
            conn.commit()
        finally:
            conn.close()

    def mark_outbox_failed(self, table_name: str, row_key: str, error: str) -> None:
        now = self._now()
        conn = self.connect()
        try:
            conn.execute(
                """
                UPDATE sync_outbox
                SET status = 'failed',
                    attempt_count = attempt_count + 1,
                    last_error = ?,
                    updated_at = ?
                WHERE table_name = ? AND row_key = ?
                """,
                (error[:500], now, table_name, row_key),
            )
            conn.commit()
        finally:
            conn.close()

    def outbox_counts(self) -> dict[str, int]:
        conn = self.connect()
        try:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS count FROM sync_outbox GROUP BY status"
            ).fetchall()
        finally:
            conn.close()
        return {str(row["status"]): int(row["count"]) for row in rows}

    def delete_outbox_for_table(self, table_name: str) -> None:
        conn = self.connect()
        try:
            conn.execute("DELETE FROM sync_outbox WHERE table_name = ?", (table_name,))
            conn.commit()
        finally:
            conn.close()

    def get_active_meters(self) -> list[dict]:
        rows = self.read_all("meters")
        return [row for row in rows if str(row.get("active", "")).upper() == "TRUE"]

    def get_meter_by_id(self, meter_id: str) -> dict | None:
        rows = self.find_rows("meters", "meter_id", meter_id)
        for row in rows:
            if str(row.get("active", "")).upper() == "TRUE":
                return row
        return None

    def _create_indexes(self, conn: sqlite3.Connection) -> None:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_meters_active ON meters(active)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_settings_key ON settings(key)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_batches_batch_id ON batches(batch_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_batches_source ON batches(line_source_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_batches_week ON batches(week)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_batches_status ON batches(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_readings_batch ON readings(batch_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_readings_meter_created ON readings(meter_id, created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_readings_source ON readings(line_source_id)")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pending_source_status_created "
            "ON pending_confirmations(line_source_id, status, created_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_pending_confirmation_id "
            "ON pending_confirmations(confirmation_id)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_event_type ON audit_log(event_type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_source ON audit_log(line_source_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON audit_log(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_outbox_status ON sync_outbox(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_outbox_updated ON sync_outbox(updated_at)")

    def _create_sync_outbox(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sync_outbox (
                table_name TEXT NOT NULL,
                row_key TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                operation TEXT NOT NULL,
                status TEXT NOT NULL,
                attempt_count INTEGER NOT NULL DEFAULT 0,
                last_error TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                synced_at TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (table_name, row_key)
            )
            """
        )

    def _headers(self, tab_name: str) -> list[str]:
        headers = TAB_HEADERS.get(tab_name)
        if not headers:
            raise ValueError(f"Unknown SQLite table '{tab_name}'")
        return headers

    def _row_to_dict(self, row: sqlite3.Row, headers: list[str]) -> dict:
        return {header: row[header] if row[header] is not None else "" for header in headers}

    def _to_text(self, value: Any) -> str:
        return "" if value is None else str(value)

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()


sqlite_client = SQLiteClient()
