"""SQLite persistence for medical records."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from app.domain.models import (
    MedicalRecord,
    RecordResponse,
    RecordStatus,
    RecordSummary,
    utcnow,
)
from app.domain.processing import ProcessingProgress


class RecordStore:
    def __init__(self, database_url: str) -> None:
        self._db_path = self._resolve_path(database_url)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @staticmethod
    def _resolve_path(database_url: str) -> Path:
        prefix = "sqlite:///"
        if not database_url.startswith(prefix):
            raise ValueError(f"Unsupported database URL: {database_url}")
        return Path(database_url.removeprefix(prefix)).expanduser().resolve()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS records (
                    id TEXT PRIMARY KEY,
                    original_filename TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    error_message TEXT,
                    raw_text TEXT,
                    structured_data TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()
            self._ensure_processing_columns(conn)

    def _ensure_processing_columns(self, conn: sqlite3.Connection) -> None:
        columns = {
            row[1] for row in conn.execute("PRAGMA table_info(records)").fetchall()
        }
        if "processing_progress" not in columns:
            conn.execute(
                "ALTER TABLE records ADD COLUMN processing_progress INTEGER"
            )
        if "processing_step" not in columns:
            conn.execute("ALTER TABLE records ADD COLUMN processing_step TEXT")
        if "processing_message" not in columns:
            conn.execute("ALTER TABLE records ADD COLUMN processing_message TEXT")

    def update_during_processing(
        self,
        record_id: str,
        *,
        raw_text: str | None = None,
        structured_data: MedicalRecord | None = None,
        progress: ProcessingProgress | None = None,
    ) -> RecordResponse:
        now = utcnow().isoformat()
        fields: list[str] = ["updated_at = ?"]
        values: list[Any] = [now]

        if raw_text is not None:
            fields.append("raw_text = ?")
            values.append(raw_text)
        if structured_data is not None:
            fields.append("structured_data = ?")
            values.append(structured_data.model_dump_json())
        if progress is not None:
            fields.extend(
                ["processing_progress = ?", "processing_step = ?", "processing_message = ?"]
            )
            values.extend([progress.percent, progress.step, progress.message])

        values.append(record_id)
        with self._connect() as conn:
            conn.execute(
                f"UPDATE records SET {', '.join(fields)} WHERE id = ?",
                tuple(values),
            )
            conn.commit()
        return self.get(record_id)

    def create(
        self,
        *,
        record_id: str,
        original_filename: str,
        stored_path: str,
        content_type: str,
        status: RecordStatus = RecordStatus.processing,
    ) -> RecordResponse:
        now = utcnow().isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO records (
                    id, original_filename, stored_path, content_type, status,
                    error_message, raw_text, structured_data, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, NULL, NULL, NULL, ?, ?)
                """,
                (
                    record_id,
                    original_filename,
                    stored_path,
                    content_type,
                    status.value,
                    now,
                    now,
                ),
            )
            conn.commit()
        return self.get(record_id)

    def update_processing_result(
        self,
        record_id: str,
        *,
        status: RecordStatus,
        raw_text: str | None = None,
        structured_data: MedicalRecord | None = None,
        error_message: str | None = None,
    ) -> RecordResponse:
        now = utcnow().isoformat()
        payload = (
            structured_data.model_dump_json() if structured_data is not None else None
        )
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE records
                SET status = ?, error_message = ?, raw_text = ?, structured_data = ?,
                    processing_progress = NULL, processing_step = NULL,
                    processing_message = NULL, updated_at = ?
                WHERE id = ?
                """,
                (status.value, error_message, raw_text, payload, now, record_id),
            )
            conn.commit()
        return self.get(record_id)

    def update_structured_data(
        self, record_id: str, structured_data: MedicalRecord
    ) -> RecordResponse:
        now = utcnow().isoformat()
        with self._connect() as conn:
            cur = conn.execute(
                """
                UPDATE records
                SET structured_data = ?, status = ?, error_message = NULL,
                    processing_progress = NULL, processing_step = NULL,
                    processing_message = NULL, updated_at = ?
                WHERE id = ?
                """,
                (
                    structured_data.model_dump_json(),
                    RecordStatus.completed.value,
                    now,
                    record_id,
                ),
            )
            if cur.rowcount == 0:
                raise KeyError(record_id)
            conn.commit()
        return self.get(record_id)

    def get(self, record_id: str) -> RecordResponse:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM records WHERE id = ?", (record_id,)
            ).fetchone()
        if row is None:
            raise KeyError(record_id)
        return self._to_response(row)

    def get_stored_path(self, record_id: str) -> str:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT stored_path FROM records WHERE id = ?", (record_id,)
            ).fetchone()
        if row is None:
            raise KeyError(record_id)
        return row["stored_path"]

    def list_records(self) -> list[RecordSummary]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM records ORDER BY created_at DESC"
            ).fetchall()
        return [self._to_summary(row) for row in rows]

    def _to_response(self, row: sqlite3.Row) -> RecordResponse:
        structured: MedicalRecord | None = None
        if row["structured_data"]:
            structured = MedicalRecord.model_validate_json(row["structured_data"])
        progress: ProcessingProgress | None = None
        if row["status"] == RecordStatus.processing.value and row["processing_progress"] is not None:
            progress = ProcessingProgress(
                percent=int(row["processing_progress"]),
                step=row["processing_step"] or "processing",
                message=row["processing_message"] or "Processing your document…",
            )
        return RecordResponse(
            id=row["id"],
            original_filename=row["original_filename"],
            content_type=row["content_type"],
            status=RecordStatus(row["status"]),
            error_message=row["error_message"],
            raw_text=row["raw_text"],
            structured_data=structured,
            processing=progress,
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def _to_summary(self, row: sqlite3.Row) -> RecordSummary:
        pet_name = None
        if row["structured_data"]:
            data: dict[str, Any] = json.loads(row["structured_data"])
            pet_name = (data.get("pet") or {}).get("name")
        return RecordSummary(
            id=row["id"],
            original_filename=row["original_filename"],
            status=RecordStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            pet_name=pet_name,
        )
