"""Unit tests for hybrid/heuristic structuring and async processing."""

from __future__ import annotations

import asyncio
from io import BytesIO
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient

from app.adapters.llm import (
    ClinicalNarrative,
    OllamaStructurer,
    _inline_json_schema,
    build_structurer,
)
from app.adapters.pdf_extractor import PdfplumberExtractor
from app.adapters.text_hints import build_layout_hints
from app.domain.extraction_models import (
    ExtractionClinicalInfo,
    ExtractionRecord,
    Medication,
)
from app.domain.models import MedicalRecord, PetInfo
from app.domain.processing import ProcessingProgress
from app.services.records import RecordService
from app.services.store import RecordStore
from tests.test_api import _make_sample_pdf_bytes
from tests.test_spanish_extraction import SPANISH_HEADER
from tests.test_inline_demographics import INLINE_NOMBRE_DOC


THIN_TEXT = """
Veterinary note
Patient seen today for checkup.
No dated visit list.
"""


@pytest.fixture()
def ollama_structurer() -> OllamaStructurer:
    return OllamaStructurer(
        base_url="http://127.0.0.1:9",
        model="qwen2.5:7b",
        timeout_seconds=1,
        clinical_mode="hybrid",
        skip_demographics_when_hinted=True,
    )


def test_clinical_hints_sufficient_for_historial(ollama_structurer: OllamaStructurer) -> None:
    hints = build_layout_hints(SPANISH_HEADER)
    assert ollama_structurer._clinical_hints_sufficient(hints) is True
    assert ollama_structurer._should_call_clinical_llm(hints) is False


def test_clinical_hints_insufficient_for_thin_text(ollama_structurer: OllamaStructurer) -> None:
    hints = build_layout_hints(THIN_TEXT)
    assert ollama_structurer._clinical_hints_sufficient(hints) is False
    assert ollama_structurer._should_call_clinical_llm(hints) is True


def test_heuristic_mode_never_calls_clinical_llm(ollama_structurer: OllamaStructurer) -> None:
    ollama_structurer.clinical_mode = "heuristic"
    thin_hints = build_layout_hints(THIN_TEXT)
    assert ollama_structurer._should_call_clinical_llm(thin_hints) is False


def test_llm_mode_always_calls_clinical_llm(ollama_structurer: OllamaStructurer) -> None:
    ollama_structurer.clinical_mode = "llm"
    rich_hints = build_layout_hints(SPANISH_HEADER)
    assert ollama_structurer._should_call_clinical_llm(rich_hints) is True


def test_clinical_from_hints_builds_visit_medications_and_diagnosis(
    ollama_structurer: OllamaStructurer,
) -> None:
    hints = build_layout_hints(SPANISH_HEADER)
    clinical = ollama_structurer._clinical_from_hints(hints)
    assert clinical.history_entries
    assert clinical.diagnosis and "Giardiasis" in clinical.diagnosis
    assert any(m.name == "Tobradex" for m in clinical.medications)
    assert any(m.name == "Fortiflora" for m in clinical.medications)
    assert clinical.chief_complaint
    assert clinical.history is None


def test_merge_narrative_overwrites_only_non_empty_fields(
    ollama_structurer: OllamaStructurer,
) -> None:
    base = ExtractionClinicalInfo(
        chief_complaint="old chief",
        history="old history",
        examination=None,
        treatment=None,
        medications=[Medication(name="Fortiflora")],
        notes="heuristic note",
    )
    narrative = ClinicalNarrative(
        chief_complaint="new chief",
        history=None,
        examination="exam ok",
        treatment="continue diet",
        notes=None,
    )
    merged = ollama_structurer._merge_narrative(base, narrative)
    assert merged.chief_complaint == "new chief"
    assert merged.history == "old history"
    assert merged.examination == "exam ok"
    assert merged.treatment == "continue diet"
    assert merged.notes == "heuristic note"
    assert merged.medications[0].name == "Fortiflora"


def test_heuristic_mode_structures_spanish_without_ollama() -> None:
    structurer = OllamaStructurer(
        base_url="http://127.0.0.1:9",
        model="unused",
        clinical_mode="heuristic",
        skip_demographics_when_hinted=True,
    )
    record = structurer.structure(SPANISH_HEADER)
    assert record.pet.name == "MARLEY"
    assert record.owner.name and "BEATRIZ" in record.owner.name
    assert record.pet.microchip == "941000024967769"
    assert record.meta.source_language == "es"
    assert record.clinical.history
    assert len(record.clinical.history) <= 2000
    assert "El expediente documenta" in record.clinical.history
    assert "MARLEY" not in record.clinical.history
    assert not hasattr(record, "visit")


def test_ollama_heuristic_splits_compound_nombre_line_without_llm(
    ollama_structurer: OllamaStructurer,
) -> None:
    record = ollama_structurer.structure(INLINE_NOMBRE_DOC)
    assert record.pet.name == "ALYA"
    assert record.pet.date_of_birth == "05/07/2018"
    assert "Nacimiento" not in (record.pet.name or "")


def test_llm_timeout_falls_back_to_heuristics_instead_of_failing() -> None:
    structurer = OllamaStructurer(
        base_url="http://127.0.0.1:9",
        model="unused",
        timeout_seconds=0.01,
        clinical_mode="llm",  # force clinical LLM call
        skip_demographics_when_hinted=True,
    )
    record = structurer.structure(SPANISH_HEADER)
    assert record.pet.name == "MARLEY"
    assert record.clinical.history


def test_demographics_llm_failure_falls_back_to_hints() -> None:
    structurer = OllamaStructurer(
        base_url="http://127.0.0.1:9",
        model="unused",
        timeout_seconds=0.01,
        clinical_mode="heuristic",
        skip_demographics_when_hinted=False,  # force demographics LLM attempt
    )
    record = structurer.structure(SPANISH_HEADER)
    assert record.pet.name == "MARLEY"
    assert record.meta.source_language == "es"


def test_empty_text_returns_low_confidence(ollama_structurer: OllamaStructurer) -> None:
    record = ollama_structurer.structure("   \n  ")
    assert record.meta.extraction_confidence == "low"
    assert "raw_text" in record.meta.missing_fields


def test_inline_json_schema_resolves_refs() -> None:
    schema = MedicalRecord.model_json_schema()
    assert "$defs" in schema
    inlined = _inline_json_schema(schema)
    assert "$defs" not in inlined
    assert "$ref" not in str(inlined)
    pet_name = inlined["properties"]["pet"]["properties"]["name"]
    assert "anyOf" in pet_name or pet_name.get("type") in {"string", None}
    assert "clinical" in inlined["properties"]


def test_build_structurer_fake_and_ollama() -> None:
    fake = build_structurer(
        provider="fake",
        base_url="http://localhost",
        model="x",
        timeout_seconds=1,
    )
    assert fake.health() == "skipped"

    ollama = build_structurer(
        provider="ollama",
        base_url="http://127.0.0.1:9",
        model="qwen2.5:7b",
        timeout_seconds=1,
        clinical_mode="hybrid",
    )
    assert isinstance(ollama, OllamaStructurer)
    assert ollama.clinical_mode == "hybrid"


def test_build_structurer_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="Unknown LLM provider"):
        build_structurer(
            provider="openai",
            base_url="http://localhost",
            model="x",
            timeout_seconds=1,
        )


def test_record_service_async_returns_processing(tmp_path: Path) -> None:
    store = RecordStore(f"sqlite:///{tmp_path / 'async.db'}")
    upload_dir = tmp_path / "uploads"
    service = RecordService(
        store=store,
        extractor=PdfplumberExtractor(),
        structurer=MagicMock(),
        upload_dir=upload_dir,
        max_upload_bytes=10_000_000,
        processing_mode="async",
    )
    pdf_bytes = _make_sample_pdf_bytes()
    upload = UploadFile(filename="buddy.pdf", file=BytesIO(pdf_bytes))
    record = asyncio.run(service.create_from_upload(upload))
    assert record.status.value == "processing"
    assert record.structured_data is None
    service.structurer.structure.assert_not_called()


def test_record_service_sync_processes_immediately(tmp_path: Path) -> None:
    store = RecordStore(f"sqlite:///{tmp_path / 'sync.db'}")
    upload_dir = tmp_path / "uploads"
    structured = MedicalRecord(pet=PetInfo(name="Buddy"))
    structurer = MagicMock()
    structurer.structure.return_value = structured
    service = RecordService(
        store=store,
        extractor=PdfplumberExtractor(),
        structurer=structurer,
        upload_dir=upload_dir,
        max_upload_bytes=10_000_000,
        processing_mode="sync",
    )
    pdf_bytes = _make_sample_pdf_bytes()
    upload = UploadFile(filename="buddy.pdf", file=BytesIO(pdf_bytes))
    record = asyncio.run(service.create_from_upload(upload))
    assert record.status.value == "completed"
    assert record.structured_data is not None
    assert record.structured_data.pet.name == "Buddy"
    structurer.structure.assert_called_once()


def test_process_record_marks_failed_on_structurer_error(tmp_path: Path) -> None:
    store = RecordStore(f"sqlite:///{tmp_path / 'fail.db'}")
    upload_dir = tmp_path / "uploads"
    structurer = MagicMock()
    structurer.structure.side_effect = RuntimeError("Ollama request failed: timed out")
    service = RecordService(
        store=store,
        extractor=PdfplumberExtractor(),
        structurer=structurer,
        upload_dir=upload_dir,
        max_upload_bytes=10_000_000,
        processing_mode="async",
    )
    pdf_bytes = _make_sample_pdf_bytes()
    upload = UploadFile(filename="buddy.pdf", file=BytesIO(pdf_bytes))
    created = asyncio.run(service.create_from_upload(upload))
    failed = service.process_record(created.id)
    assert failed.status.value == "failed"
    assert "timed out" in (failed.error_message or "")


def test_api_async_mode_returns_processing_then_completes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "api-async.db"
    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("PROCESSING_MODE", "async")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")

    from app import config, dependencies

    config.get_settings.cache_clear()
    dependencies.get_store.cache_clear()
    dependencies.get_extractor.cache_clear()
    dependencies.get_structurer.cache_clear()

    from app.main import create_app

    app = create_app()
    with TestClient(app) as client:
        response = client.post(
            "/api/records",
            files={"file": ("buddy.pdf", _make_sample_pdf_bytes(), "application/pdf")},
        )
        assert response.status_code == 201
        body = response.json()
        assert body["status"] == "processing"
        record_id = body["id"]

        # BackgroundTasks run after the request in TestClient.
        detail = client.get(f"/api/records/{record_id}")
        assert detail.status_code == 200
        assert detail.json()["status"] == "completed"
        assert detail.json()["structured_data"]["pet"]["name"] == "Buddy"

    config.get_settings.cache_clear()
    dependencies.get_store.cache_clear()
    dependencies.get_extractor.cache_clear()
    dependencies.get_structurer.cache_clear()


def test_update_during_processing_persists_progress_and_partial_data(tmp_path: Path) -> None:
    store = RecordStore(f"sqlite:///{tmp_path / 'progress.db'}")
    record = store.create(
        record_id="rec-progress",
        original_filename="buddy.pdf",
        stored_path=str(tmp_path / "buddy.pdf"),
        content_type="application/pdf",
    )
    partial = MedicalRecord(pet=PetInfo(name="EarlyPet"))
    updated = store.update_during_processing(
        record.id,
        structured_data=partial,
        progress=ProcessingProgress(
            percent=35,
            step="demographics",
            message="Pet and owner details are ready.",
        ),
    )
    assert updated.status.value == "processing"
    assert updated.processing is not None
    assert updated.processing.percent == 35
    assert updated.processing.message == "Pet and owner details are ready."
    assert updated.structured_data is not None
    assert updated.structured_data.pet.name == "EarlyPet"

    from app.domain.models import RecordStatus

    completed = store.update_processing_result(
        record.id,
        status=RecordStatus.completed,
        structured_data=MedicalRecord(pet=PetInfo(name="FinalPet")),
    )
    assert completed.processing is None
    assert completed.structured_data.pet.name == "FinalPet"


def test_process_record_passes_progress_callbacks_to_structurer(tmp_path: Path) -> None:
    store = RecordStore(f"sqlite:///{tmp_path / 'callbacks.db'}")
    upload_dir = tmp_path / "uploads"
    partial = MedicalRecord(pet=PetInfo(name="Partial"))
    final = MedicalRecord(pet=PetInfo(name="Final"))

    def structure(raw_text, on_progress=None, on_partial=None):
        if on_progress:
            on_progress(
                ProcessingProgress(
                    percent=50,
                    step="clinical_analysis",
                    message="Reviewing visits…",
                )
            )
        if on_partial:
            on_partial(partial)
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
    pdf_bytes = _make_sample_pdf_bytes()
    upload = UploadFile(filename="buddy.pdf", file=BytesIO(pdf_bytes))
    created = asyncio.run(service.create_from_upload(upload))
    result = service.process_record(created.id)

    structurer.structure.assert_called_once()
    call_kwargs = structurer.structure.call_args.kwargs
    assert call_kwargs["on_progress"] is not None
    assert call_kwargs["on_partial"] is not None
    assert result.status.value == "completed"
    assert result.structured_data.pet.name == "Final"
