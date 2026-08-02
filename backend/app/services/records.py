"""Record processing use cases."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from fastapi import UploadFile

from app.adapters.llm import MedicalRecordStructurer
from app.adapters.document_extractor import (
    CompositeDocumentExtractor,
    DocumentTextExtractor,
    resolve_upload_format,
)
from app.domain.models import MedicalRecord, RecordResponse, RecordStatus, new_record_id
from app.domain.processing import ProcessingProgress
from app.services.store import RecordStore

ProgressCallback = Callable[[ProcessingProgress], None]
PartialCallback = Callable[[MedicalRecord], None]


class RecordService:
    def __init__(
        self,
        *,
        store: RecordStore,
        extractor: DocumentTextExtractor,
        structurer: MedicalRecordStructurer,
        upload_dir: Path,
        max_upload_bytes: int,
        processing_mode: str = "async",
    ) -> None:
        self.store = store
        self.extractor = extractor
        self.structurer = structurer
        self.upload_dir = upload_dir
        self.max_upload_bytes = max_upload_bytes
        self.processing_mode = processing_mode
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def create_from_upload(self, file: UploadFile) -> RecordResponse:
        filename = file.filename or "upload.pdf"
        content_type = file.content_type or ""

        try:
            extension, canonical_type = resolve_upload_format(filename, content_type)
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        data = await file.read()
        if not data:
            raise ValueError("Uploaded file is empty")
        if len(data) > self.max_upload_bytes:
            raise ValueError(
                f"File exceeds maximum size of {self.max_upload_bytes} bytes"
            )

        record_id = new_record_id()
        stored_name = f"{record_id}{extension}"
        stored_path = self.upload_dir / stored_name
        stored_path.write_bytes(data)

        record = self.store.create(
            record_id=record_id,
            original_filename=filename,
            stored_path=str(stored_path),
            content_type=canonical_type,
            status=RecordStatus.processing,
        )

        if self.processing_mode == "sync":
            return self.process_record(record_id)

        return record

    def process_record(self, record_id: str) -> RecordResponse:
        """Extract text and structure the record (runs sync or in background)."""
        try:
            self.store.update_during_processing(
                record_id,
                progress=ProcessingProgress(
                    percent=5,
                    step="starting",
                    message="Starting to process your document…",
                ),
            )
            stored_path = Path(self.store.get_stored_path(record_id))
            raw_text = self.extractor.extract(stored_path)
            self.store.update_during_processing(
                record_id,
                raw_text=raw_text,
                progress=ProcessingProgress(
                    percent=15,
                    step="extracting_text",
                    message="Reading text from your document…",
                ),
            )

            def on_progress(progress: ProcessingProgress) -> None:
                self.store.update_during_processing(record_id, progress=progress)

            def on_partial(partial: MedicalRecord) -> None:
                self.store.update_during_processing(
                    record_id,
                    structured_data=partial,
                    progress=ProcessingProgress(
                        percent=35,
                        step="demographics",
                        message="Pet and owner details are ready. Clinical summary in progress…",
                    ),
                )

            structured = self.structurer.structure(
                raw_text,
                on_progress=on_progress,
                on_partial=on_partial,
            )
            return self.store.update_processing_result(
                record_id,
                status=RecordStatus.completed,
                raw_text=raw_text,
                structured_data=structured,
            )
        except Exception as exc:
            return self.store.update_processing_result(
                record_id,
                status=RecordStatus.failed,
                raw_text=None,
                structured_data=None,
                error_message=str(exc),
            )
