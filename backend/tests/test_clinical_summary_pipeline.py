"""Integration tests for the clinical summary structuring pipeline."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from app.adapters.clinical_summary import (
    CLINICAL_SUMMARY_PROMPT,
    ClinicalSummaryOutput,
)
from app.adapters.llm import OllamaStructurer
from app.domain.extraction_models import (
    ExtractionClinicalInfo,
    ExtractionRecord,
    VisitInfo,
    to_persisted_record,
)
from app.domain.models import MetaInfo, OwnerInfo, PetInfo
from tests.test_spanish_extraction import SPANISH_HEADER


@pytest.fixture()
def llm_structurer() -> OllamaStructurer:
    return OllamaStructurer(
        base_url="http://127.0.0.1:9",
        model="unused",
        clinical_mode="llm",
        skip_demographics_when_hinted=True,
    )


class TestProduceClinicalSummary:
    def test_llm_success_sets_source_and_uses_llm_text(
        self, llm_structurer: OllamaStructurer
    ) -> None:
        llm_text = (
            "Paciente con historial de giardiasis y conjuntivitis. "
            "Visitas previas documentan diarrea y tratamiento antiparasitario."
        )
        llm_structurer._chat_model = MagicMock(
            return_value=ClinicalSummaryOutput(summary=llm_text)
        )

        record = llm_structurer.structure(SPANISH_HEADER)

        assert record.meta.clinical_summary_source == "llm"
        assert record.clinical.history == llm_text
        assert "El expediente documenta" not in record.clinical.history
        llm_structurer._chat_model.assert_called_once()
        call_kwargs = llm_structurer._chat_model.call_args.kwargs
        assert call_kwargs["system"] == CLINICAL_SUMMARY_PROMPT
        assert "Structured facts" not in call_kwargs["user"]
        assert "Extraction hints" not in call_kwargs["user"]
        assert "SOURCE TEXT" in call_kwargs["user"]

    def test_llm_user_prompt_prefers_historial_section(
        self, llm_structurer: OllamaStructurer
    ) -> None:
        captured: dict[str, str] = {}

        def capture_chat(**kwargs):
            captured["user"] = kwargs["user"]
            return ClinicalSummaryOutput(summary="Resumen clínico generado por IA.")

        llm_structurer._chat_model = MagicMock(side_effect=capture_chat)
        llm_structurer.structure(SPANISH_HEADER)

        assert "Historial" in captured["user"] or "historial" in captured["user"].lower()

    def test_empty_llm_response_falls_back_to_heuristic(
        self, llm_structurer: OllamaStructurer
    ) -> None:
        llm_structurer._chat_model = MagicMock(
            return_value=ClinicalSummaryOutput(summary="   ")
        )

        record = llm_structurer.structure(SPANISH_HEADER)

        assert record.meta.clinical_summary_source == "heuristic_fallback"
        assert record.clinical.history
        assert "El expediente documenta" in record.clinical.history

    def test_llm_exception_falls_back_to_heuristic(
        self, llm_structurer: OllamaStructurer
    ) -> None:
        llm_structurer._chat_model = MagicMock(
            side_effect=RuntimeError("Ollama request failed: timed out")
        )

        record = llm_structurer.structure(SPANISH_HEADER)

        assert record.meta.clinical_summary_source == "heuristic_fallback"
        assert record.clinical.history
        assert "Giardiasis" in record.clinical.history or "giardia" in record.clinical.history.lower()

    def test_hybrid_timeout_also_marks_heuristic_fallback(self) -> None:
        structurer = OllamaStructurer(
            base_url="http://127.0.0.1:9",
            model="unused",
            timeout_seconds=0.01,
            clinical_mode="hybrid",
            skip_demographics_when_hinted=True,
        )
        record = structurer.structure(SPANISH_HEADER)
        assert record.meta.clinical_summary_source == "heuristic_fallback"

    def test_heuristic_mode_never_calls_llm(
        self, llm_structurer: OllamaStructurer
    ) -> None:
        llm_structurer.clinical_mode = "heuristic"
        llm_structurer._chat_model = MagicMock()

        record = llm_structurer.structure(SPANISH_HEADER)

        llm_structurer._chat_model.assert_not_called()
        assert record.meta.clinical_summary_source == "heuristic"
        assert "El expediente documenta" in record.clinical.history

    def test_skips_summary_when_no_clinical_hints(self) -> None:
        structurer = OllamaStructurer(
            base_url="http://127.0.0.1:9",
            model="unused",
            clinical_mode="llm",
            skip_demographics_when_hinted=True,
        )
        structurer._chat_model = MagicMock()

        thin_text = "Vet clinic\nBuddy\nDog\nJane Doe\n"
        record = structurer.structure(thin_text)

        structurer._chat_model.assert_not_called()
        assert record.meta.clinical_summary_source is None
        assert record.clinical.history is None

    def test_partial_callback_omits_summary_and_source(
        self, llm_structurer: OllamaStructurer
    ) -> None:
        llm_structurer._chat_model = MagicMock(
            return_value=ClinicalSummaryOutput(summary="Resumen generado por IA.")
        )
        partials = []
        llm_structurer.structure(
            SPANISH_HEADER,
            on_partial=lambda record: partials.append(record),
        )

        assert len(partials) == 1
        assert partials[0].pet.name == "MARLEY"
        assert partials[0].clinical.history is None
        assert partials[0].meta.clinical_summary_source is None


class TestVisitMetaAndPersistence:
    def test_apply_visit_and_meta_uses_hints_without_clinical_workspace(self) -> None:
        record = ExtractionRecord(
            pet=PetInfo(name="MARLEY"),
            owner=OwnerInfo(),
            visit=VisitInfo(),
            clinical=ExtractionClinicalInfo(),
            meta=MetaInfo(),
        )
        hints = {
            "visit_blocks": [{"date": "08/12/19", "summary": "Urgencias"}],
            "likely_fields": {"visit.clinic_name": "Parque Oeste"},
            "visit_dates_found": ["08/12/19", "03/10/20"],
        }

        updated = OllamaStructurer._apply_visit_and_meta(record, hints)

        assert updated.meta.extraction_confidence == "high"
        assert updated.visit.clinic_name == "Parque Oeste"
        assert updated.visit.date == "03/10/20"
        assert not updated.clinical.diagnosis

    def test_to_persisted_record_preserves_clinical_summary_source(self) -> None:
        record = ExtractionRecord(
            pet=PetInfo(name="MARLEY"),
            owner=OwnerInfo(name="Owner"),
            visit=VisitInfo(),
            clinical=ExtractionClinicalInfo(history="Resumen clínico."),
            meta=MetaInfo(
                source_language="es",
                extraction_confidence="high",
                clinical_summary_source="llm",
            ),
        )

        persisted = to_persisted_record(record)

        assert persisted.meta.clinical_summary_source == "llm"
        assert persisted.clinical.history == "Resumen clínico."
