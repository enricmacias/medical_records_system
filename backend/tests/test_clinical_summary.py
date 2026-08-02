"""Tests for extraction-time clinical summary generation."""

from app.adapters.clinical_summary import (
    CLINICAL_SUMMARY_MAX,
    build_heuristic_clinical_summary,
    clinical_facts_payload,
    finalize_clinical_summary,
    has_clinical_content,
    summary_polish_user_prompt,
    truncate_clinical_summary,
)
from app.adapters.llm import FakeLLMStructurer
from app.domain.extraction_models import (
    ExtractionClinicalInfo,
    ExtractionRecord,
    HistoryEntry,
    Medication,
    VisitInfo,
)
from app.domain.models import MedicalRecord, MetaInfo, OwnerInfo, PetInfo
from tests.test_spanish_extraction import SPANISH_HEADER


def _record(
    *,
    clinical: ExtractionClinicalInfo | None = None,
    meta: MetaInfo | None = None,
    pet: PetInfo | None = None,
    owner: OwnerInfo | None = None,
    visit: VisitInfo | None = None,
) -> ExtractionRecord:
    return ExtractionRecord(
        pet=pet or PetInfo(),
        owner=owner or OwnerInfo(),
        visit=visit or VisitInfo(),
        clinical=clinical or ExtractionClinicalInfo(),
        meta=meta or MetaInfo(),
    )


class TestHeuristicProseTemplates:
    def test_spanish_prose_includes_diagnosis_visits_and_meds(self) -> None:
        record = _record(
            pet=PetInfo(name="MARLEY"),
            owner=OwnerInfo(name="Owner"),
            clinical=ExtractionClinicalInfo(
                diagnosis="Giardiasis; Conjuntivitis",
                chief_complaint="Conjuntiva inflamada",
                treatment="Dietas digestivas",
                medications=[
                    Medication(name="Tobradex"),
                    Medication(name="Fortiflora"),
                ],
                history_entries=[
                    HistoryEntry(date="08/12/19", summary="Urgencias por costrita"),
                    HistoryEntry(date="03/10/20", summary="Conjuntivitis"),
                ],
            ),
            meta=MetaInfo(source_language="es"),
        )
        summary = build_heuristic_clinical_summary(record)
        assert "El expediente documenta" in summary
        assert "Giardiasis" in summary
        assert "08/12/19" in summary
        assert "Medicación relevante" in summary
        assert "Tobradex" in summary and "Fortiflora" in summary
        assert "MARLEY" not in summary
        assert len(summary) <= CLINICAL_SUMMARY_MAX

    def test_english_prose_includes_diagnosis_visits_and_meds(self) -> None:
        record = _record(
            clinical=ExtractionClinicalInfo(
                diagnosis="Otitis externa",
                chief_complaint="Ear scratching",
                examination="Erythema in left canal",
                treatment="Topical drops",
                medications=[Medication(name="Otomax")],
                history_entries=[
                    HistoryEntry(date="2024-06-10", summary="Follow-up visit"),
                ],
            ),
            meta=MetaInfo(source_language="en"),
        )
        summary = build_heuristic_clinical_summary(record)
        assert summary.startswith("The record documents Otitis externa.")
        assert "Recent concern: Ear scratching." in summary
        assert "Examination findings include" in summary
        assert "Visit history notes that on 2024-06-10, Follow-up visit." in summary
        assert "Treatment and management: Topical drops." in summary
        assert "Relevant medications include Otomax." in summary

    def test_single_visit_uses_singular_visit_phrase(self) -> None:
        record = _record(
            clinical=ExtractionClinicalInfo(
                diagnosis="Giardiasis",
                history_entries=[
                    HistoryEntry(date="08/12/19", summary="Urgencias por costrita"),
                ],
            ),
            meta=MetaInfo(source_language="es"),
        )
        summary = build_heuristic_clinical_summary(record)
        assert "En el historial de visitas se anota que" in summary
        assert "A lo largo de las visitas" not in summary

    def test_summary_uses_paragraph_breaks(self) -> None:
        record = _record(
            clinical=ExtractionClinicalInfo(
                diagnosis="Otitis",
                treatment="Drops",
                medications=[Medication(name="Otomax")],
            ),
            meta=MetaInfo(source_language="en"),
        )
        summary = build_heuristic_clinical_summary(record)
        assert "\n\n" in summary


class TestSanitizationAndFiltering:
    def test_removes_weight_and_medication_names_from_visit_snippets(self) -> None:
        record = _record(
            clinical=ExtractionClinicalInfo(
                diagnosis="Giardiasis",
                medications=[
                    Medication(name="Tobradex"),
                    Medication(name="Fortiflora"),
                ],
                history_entries=[
                    HistoryEntry(
                        date="03/10/20",
                        summary=(
                            "Conjuntiva inflamada. Test de giardia: positivo!! "
                            "Peso 29.6kg Tobradex y Fortiflora."
                        ),
                    ),
                ],
            ),
            meta=MetaInfo(source_language="es"),
        )
        summary = build_heuristic_clinical_summary(record)
        assert "29.6" not in summary
        assert "29.6kg" not in summary.lower()
        assert "Tobradex" in summary and "Fortiflora" in summary
        assert summary.count("Tobradex") == 1

    def test_skips_redundant_chief_complaint_matching_last_visit(self) -> None:
        record = _record(
            clinical=ExtractionClinicalInfo(
                diagnosis="Conjuntivitis",
                chief_complaint="Conjuntiva inflamada. Test de giardia: positivo!!",
                history_entries=[
                    HistoryEntry(
                        date="03/10/20",
                        summary="Conjuntiva inflamada. Test de giardia: positivo!!",
                    ),
                ],
            ),
            meta=MetaInfo(source_language="es"),
        )
        summary = build_heuristic_clinical_summary(record)
        assert "Motivo de consulta reciente" not in summary
        assert "Conjuntiva inflamada" in summary

    def test_excludes_generic_pipeline_notes(self) -> None:
        record = _record(
            clinical=ExtractionClinicalInfo(
                diagnosis="Giardiasis",
                notes="Documento en español con historial multi-visita.",
            ),
            meta=MetaInfo(source_language="es"),
        )
        summary = build_heuristic_clinical_summary(record)
        assert "Documento en español" not in summary
        assert "multi-visita" not in summary

    def test_includes_clinically_relevant_notes(self) -> None:
        record = _record(
            clinical=ExtractionClinicalInfo(
                diagnosis="Otitis",
                notes="Follow up in one week if symptoms persist.",
            ),
            meta=MetaInfo(source_language="en"),
        )
        summary = build_heuristic_clinical_summary(record)
        assert "Follow up in one week" in summary


class TestTruncateClinicalSummary:
    def test_truncates_long_unbroken_text_to_max_with_ellipsis(self) -> None:
        long_text = "a" * (CLINICAL_SUMMARY_MAX + 50)
        truncated = truncate_clinical_summary(long_text)
        assert len(truncated) == CLINICAL_SUMMARY_MAX
        assert truncated.endswith("…")

    def test_truncates_at_paragraph_boundary_when_possible(self) -> None:
        first = "First paragraph sentence."
        second = "b" * (CLINICAL_SUMMARY_MAX - 20)
        text = f"{first}\n\n{second}"
        truncated = truncate_clinical_summary(text)
        assert len(truncated) <= CLINICAL_SUMMARY_MAX
        assert truncated.endswith("…")
        assert truncated.startswith("First paragraph sentence.")

    def test_truncates_at_sentence_boundary_when_no_paragraph_fit(self) -> None:
        prefix = "Intro. "
        remainder = "word " * 800
        text = prefix + remainder
        truncated = truncate_clinical_summary(text)
        assert len(truncated) <= CLINICAL_SUMMARY_MAX
        assert truncated.endswith("…")
        assert truncated.startswith("Intro.")

    def test_preserves_short_text(self) -> None:
        text = "Short clinical summary."
        assert truncate_clinical_summary(text) == text


class TestFinalizeAndHelpers:
    def test_finalize_sets_clinical_history_from_heuristic(self) -> None:
        record = _record(
            clinical=ExtractionClinicalInfo(
                diagnosis="Otitis",
                medications=[Medication(name="Otomax")],
            ),
            meta=MetaInfo(source_language="en"),
        )
        finalized = finalize_clinical_summary(record)
        assert finalized.clinical.history
        assert "Otitis" in finalized.clinical.history
        assert "Otomax" in finalized.clinical.history

    def test_finalize_clears_history_when_no_clinical_content(self) -> None:
        record = _record(clinical=ExtractionClinicalInfo())
        finalized = finalize_clinical_summary(record)
        assert finalized.clinical.history is None

    def test_has_clinical_content_from_structured_fields(self) -> None:
        record = _record(clinical=ExtractionClinicalInfo(diagnosis="Otitis"))
        assert has_clinical_content(record, {}) is True

    def test_has_clinical_content_from_hints_when_fields_empty(self) -> None:
        record = _record(clinical=ExtractionClinicalInfo())
        hints = {"visit_blocks": [{"date": "01/01/20", "summary": "Visit"}]}
        assert has_clinical_content(record, hints) is True

    def test_has_clinical_content_false_for_generic_notes_only(self) -> None:
        record = _record(
            clinical=ExtractionClinicalInfo(
                notes="Structured mainly from layout/visit heuristics.",
            ),
        )
        assert has_clinical_content(record, {}) is False

    def test_clinical_facts_payload_nulls_generic_notes(self) -> None:
        record = _record(
            clinical=ExtractionClinicalInfo(
                diagnosis="Otitis",
                notes="LLM narrative skipped due to timeout.",
            ),
        )
        facts = clinical_facts_payload(record)
        assert facts["diagnosis"] == "Otitis"
        assert facts["notes"] is None

    def test_summary_polish_user_prompt_includes_facts_baseline_and_source(self) -> None:
        record = _record(
            clinical=ExtractionClinicalInfo(
                diagnosis="Giardiasis",
                history_entries=[HistoryEntry(date="08/12/19", summary="Urgencias")],
            ),
            meta=MetaInfo(source_language="es"),
        )
        hints = {
            "diagnosis_hints": ["Giardiasis"],
            "medication_hints": [{"name": "Fortiflora"}],
            "visit_blocks": [{"date": "08/12/19", "summary": "Urgencias"}],
        }
        prompt = summary_polish_user_prompt(
            "Baseline draft.",
            hints,
            "Clinical body text about giardia.",
            record=record,
        )
        assert "Structured facts:" in prompt
        assert "Giardiasis" in prompt
        assert "Baseline draft." in prompt
        assert "Clinical body text about giardia." in prompt
        assert "Extraction hints:" in prompt


class TestFakeLLMIntegration:
    def test_spanish_header_generates_readable_spanish_summary(self) -> None:
        record = FakeLLMStructurer().structure(SPANISH_HEADER)
        assert isinstance(record, MedicalRecord)
        summary = record.clinical.history
        assert summary
        assert len(summary) <= CLINICAL_SUMMARY_MAX
        assert "MARLEY" not in summary
        assert "BEATRIZ" not in summary.upper()
        assert "El expediente documenta" in summary
        assert "29.6" not in summary
        assert "Medicación relevante" in summary
        assert "\n\n" in summary
        assert record.model_dump().get("visit") is None

    def test_english_fixture_generates_english_summary(self) -> None:
        english_text = (
            "Sunshine Vet Clinic\n"
            "Buddy\nDog\n"
            "Jane Doe\n"
            "Otitis externa. Otomax 4 drops twice daily.\n"
            "Left ear scratching for 3 days.\n"
            "Mild erythema in left ear canal.\n"
            "Topical ear medication.\n"
            "Follow up in 1 week.\n"
        )
        record = FakeLLMStructurer().structure(english_text)
        summary = record.clinical.history
        assert summary
        assert "The record documents" in summary or "Otitis" in summary
        assert "Buddy" not in summary
        assert "Jane Doe" not in summary
