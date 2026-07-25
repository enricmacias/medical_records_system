"""Record processing use cases."""

from __future__ import annotations

from pathlib import Path

from fastapi import UploadFile

from app.adapters.llm import MedicalRecordStructurer
from app.adapters.pdf_extractor import PdfTextExtractor
from app.domain.models import RecordResponse, RecordStatus, new_record_id
from app.services.store import RecordStore


class RecordService:
    def __init__(
        self,
        *,
        store: RecordStore,
        extractor: PdfTextExtractor,
        structurer: MedicalRecordStructurer,
        upload_dir: Path,
        max_upload_bytes: int,
    ) -> None:
        self.store = store
        self.extractor = extractor
        self.structurer = structurer
        self.upload_dir = upload_dir
        self.max_upload_bytes = max_upload_bytes
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def create_from_upload(self, file: UploadFile) -> RecordResponse:
        filename = file.filename or "upload.pdf"
        content_type = file.content_type or "application/pdf"

        if not filename.lower().endswith(".pdf") and content_type != "application/pdf":
            raise ValueError("Only PDF files are supported")

        data = await file.read()
        if not data:
            raise ValueError("Uploaded file is empty")
        if len(data) > self.max_upload_bytes:
            raise ValueError(
                f"File exceeds maximum size of {self.max_upload_bytes} bytes"
            )

        record_id = new_record_id()
        stored_name = f"{record_id}.pdf"
        stored_path = self.upload_dir / stored_name
        stored_path.write_bytes(data)

        record = self.store.create(
            record_id=record_id,
            original_filename=filename,
            stored_path=str(stored_path),
            content_type="application/pdf",
            status=RecordStatus.processing,
        )

        try:
            raw_text = self.extractor.extract(stored_path)
            structured = self.structurer.structure(raw_text)
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
