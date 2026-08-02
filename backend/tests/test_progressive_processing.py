"""Tests for progressive record processing and processing progress API."""

from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

from app.adapters.llm import FakeLLMStructurer
from app.adapters.pdf_extractor import PdfplumberExtractor
from app.domain.models import ClinicalInfo, MedicalRecord, PetInfo, RecordStatus
from app.domain.processing import ProcessingProgress
from app.services.records import RecordService
from app.services.store import RecordStore
from tests.sample_documents import make_sample_pdf_bytes
from tests.test_spanish_extraction import SPANISH_HEADER


def test_fake_llm_emits_progress_and_partial_callbacks() -> None:
    progress_events: list[ProcessingProgress] = []
    partial_records: list[MedicalRecord] = []

    record = FakeLLMStructurer().structure(
        SPANISH_HEADER,
        on_progress=lambda p: progress_events.append(p),
        on_partial=lambda r: partial_records.append(r),
    )

    assert record.pet.name == "MARLEY"
    assert len(progress_events) >= 4
    assert progress_events[0].step == "demographics"
    assert progress_events[0].percent == 20
    assert any(e.step == "clinical_summary" for e in progress_events)
    assert any(e.percent >= 95 for e in progress_events)

    assert len(partial_records) == 1
    assert partial_records[0].pet.name == "MARLEY"
    assert partial_records[0].clinical.history is None


def test_process_record_persists_partial_data_before_completion(tmp_path: Path) -> None:
    store = RecordStore(f"sqlite:///{tmp_path / 'partial.db'}")
    upload_dir = tmp_path / "uploads"
    partial = MedicalRecord(pet=PetInfo(name="PartialPet"))
    final = MedicalRecord(
        pet=PetInfo(name="FinalPet"),
        clinical=ClinicalInfo(history="Summary ready."),
    )
    record_id: str | None = None

    def structure(raw_text, on_progress=None, on_partial=None):
        if on_partial:
            on_partial(partial)
            mid = store.get(record_id)
            assert mid.structured_data is not None
            assert mid.structured_data.pet.name == "PartialPet"
            assert mid.processing is not None
            assert mid.processing.percent == 35
            assert "Clinical summary in progress" in mid.processing.message
        return final

    structurer = MagicMock()
    structurer.structure.side_effect = structure
    service = RecordService(
        store=store,
        extractor=PdfplumberExtractor(),
        structurer=structurer,
        upload_dir=upload_dir,
        max_upload_bytes=10_000_000,
        processing_mode="async",
    )
    pdf_bytes = make_sample_pdf_bytes()
    upload = UploadFile(filename="buddy.pdf", file=BytesIO(pdf_bytes))
    created = asyncio.run(service.create_from_upload(upload))
    record_id = created.id
    result = service.process_record(record_id)

    assert result.status.value == "completed"
    assert result.processing is None
    assert result.structured_data.pet.name == "FinalPet"
    assert result.structured_data.clinical.history == "Summary ready."


def test_get_record_api_returns_processing_progress(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "api-progress.db"
    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("PROCESSING_MODE", "sync")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")

    from app import config, dependencies

    config.get_settings.cache_clear()
    dependencies.get_store.cache_clear()
    dependencies.get_extractor.cache_clear()
    dependencies.get_structurer.cache_clear()

    from app.main import create_app

    store = RecordStore(f"sqlite:///{db_path}")
    record = store.create(
        record_id="rec-api-progress",
        original_filename="buddy.pdf",
        stored_path=str(upload_dir / "buddy.pdf"),
        content_type="application/pdf",
    )
    store.update_during_processing(
        record.id,
        structured_data=MedicalRecord(pet=PetInfo(name="Early")),
        progress=ProcessingProgress(
            percent=65,
            step="clinical_summary",
            message="Writing the clinical summary…",
        ),
    )

    app = create_app()
    with TestClient(app) as client:
        response = client.get(f"/api/records/{record.id}")
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "processing"
        assert body["structured_data"]["pet"]["name"] == "Early"
        assert body["processing"]["percent"] == 65
        assert body["processing"]["step"] == "clinical_summary"
        assert body["processing"]["message"] == "Writing the clinical summary…"

    config.get_settings.cache_clear()
    dependencies.get_store.cache_clear()
    dependencies.get_extractor.cache_clear()
    dependencies.get_structurer.cache_clear()


def test_completed_record_has_no_processing_in_store(tmp_path: Path) -> None:
    store = RecordStore(f"sqlite:///{tmp_path / 'completed.db'}")
    record = store.create(
        record_id="rec-done",
        original_filename="buddy.pdf",
        stored_path=str(tmp_path / "buddy.pdf"),
        content_type="application/pdf",
    )
    completed = store.update_processing_result(
        record.id,
        status=RecordStatus.completed,
        structured_data=MedicalRecord(pet=PetInfo(name="Buddy")),
    )
    assert completed.processing is None


def test_failed_record_clears_processing(tmp_path: Path) -> None:
    store = RecordStore(f"sqlite:///{tmp_path / 'failed.db'}")
    record = store.create(
        record_id="rec-fail",
        original_filename="buddy.pdf",
        stored_path=str(tmp_path / "buddy.pdf"),
        content_type="application/pdf",
    )
    store.update_during_processing(
        record.id,
        progress=ProcessingProgress(
            percent=50,
            step="clinical_analysis",
            message="Reviewing visits…",
        ),
    )
    failed = store.update_processing_result(
        record.id,
        status=RecordStatus.failed,
        error_message="LLM timeout",
    )
    assert failed.processing is None
    assert failed.status.value == "failed"
