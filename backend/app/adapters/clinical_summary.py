"""Clinical summary (clinical.history) generated at extraction time."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.domain.extraction_models import (
    ExtractionClinicalInfo,
    ExtractionRecord,
    HistoryEntry,
    Medication,
)

CLINICAL_SUMMARY_MAX = 2000
CLINICAL_SUMMARY_NUM_PREDICT = 1024


class ClinicalSummaryOutput(BaseModel):
    """Single-field structured output for the clinical summary LLM pass."""

    summary: str | None = Field(
        default=None,
        description="Readable clinical summary excluding pet/owner demographics, max 2000 characters.",
    )


_GENERIC_NOTES = (
    "documento en español",
    "historial multi-visita",
    "multi-visita",
)

_WEIGHT_RE = re.compile(r"\b(?:peso|weight)\s*[:\s]*[\d.,]+\s*kg\b", re.IGNORECASE)
_CHIP_RE = re.compile(r"\b\d{9,15}\b")

CLINICAL_SUMMARY_PROMPT = """You write clinical summaries for veterinarians reviewing imported medical records.

Return JSON with a single `summary` field containing readable prose for a human reader.

Requirements:
- Maximum 2000 characters in `summary`.
- Write 1–4 short paragraphs with complete sentences (not bullet fragments or label dumps).
- Synthesize the most important clinical information across the whole document.
- Include when present: key diagnoses/problems, visit timeline with dates where useful, examination findings, treatments/plans, and a brief mention of relevant medications (drug names only — not a full pharmacy list).
- Use the document language (Spanish or English) when clear from the source.
- Use ONLY facts from the source text. Never invent diagnoses, drugs, or dates.

Forbidden in the summary:
- Pet demographics (name, species, breed, sex, date of birth, microchip).
- Owner/client identity or contact details (name, phone, email, address).
- Generic headers like "Historial con N visitas desde…" unless clinically meaningful.
"""


def _is_spanish(record: ExtractionRecord) -> bool:
    lang = (record.meta.source_language or "").lower()
    return lang.startswith("es")


def _sanitize_summary_fragment(text: str, medication_names: list[str]) -> str:
    """Drop pet-weight lines and med names already listed in the medications section."""
    cleaned = _WEIGHT_RE.sub("", text)
    cleaned = _CHIP_RE.sub("", cleaned)
    for name in medication_names:
        if not name:
            continue
        cleaned = re.sub(rf"\b{re.escape(name)}\b", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+(?:y|and)\s*([,.;!?]|$)", r"\1", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"([,.;!?])\s*(?:y|and)\s*", r"\1 ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)
    cleaned = re.sub(r"\s+([,.;])", r"\1", cleaned)
    return cleaned.strip(" ,.;")


def _chief_complaint_for_summary(
    clinical: ExtractionClinicalInfo, medication_names: list[str]
) -> str | None:
    chief = (clinical.chief_complaint or "").strip()
    if not chief:
        return None
    entries = clinical.history_entries or []
    if entries:
        last_summary = (entries[-1].summary or "").strip()
        if last_summary:
            chief_first = chief.split(".")[0].strip()
            last_first = last_summary.split(".")[0].strip()
            if chief == last_summary or chief_first == last_first:
                return None
    sanitized = _sanitize_summary_fragment(chief, medication_names)
    return sanitized or None


def truncate_clinical_summary(text: str, max_len: int = CLINICAL_SUMMARY_MAX) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    if len(cleaned) <= max_len:
        return cleaned
    if max_len <= 1:
        return "…"[:max_len]

    ellipsis = "…"
    room = max_len - len(ellipsis)
    if room <= 0:
        return ellipsis[:max_len]

    chunk = cleaned[:room]
    last_para = chunk.rfind("\n\n")
    if last_para >= int(room * 0.55):
        candidate = cleaned[:last_para].rstrip() + "\n\n" + ellipsis
        if len(candidate) <= max_len:
            return candidate

    last_sentence = max(chunk.rfind(". "), chunk.rfind(".\n"))
    if last_sentence >= int(room * 0.6):
        candidate = cleaned[: last_sentence + 1].rstrip() + " " + ellipsis
        if len(candidate) <= max_len:
            return candidate

    return chunk.rstrip() + ellipsis


def _is_generic_note(text: str | None) -> bool:
    if not text:
        return True
    lower = text.lower()
    return any(marker in lower for marker in _GENERIC_NOTES)


def _ensure_sentence(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    if stripped[-1] in ".!?":
        return stripped
    return f"{stripped}."


def _normalize_list_field(value: str) -> str:
    return re.sub(r"\s*;\s*", ", ", value.strip())


def _medication_names(medications: list[Medication]) -> list[str]:
    names: list[str] = []
    for med in medications or []:
        name = (med.name or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def _format_medications_paragraph(
    medications: list[Medication], *, spanish: bool = False
) -> str | None:
    names = _medication_names(medications)
    if not names:
        return None
    shown = names[:8]
    if len(shown) == 1:
        body = shown[0]
    elif len(shown) == 2:
        body = f"{shown[0]} y {shown[1]}" if spanish else f"{shown[0]} and {shown[1]}"
    else:
        sep = ", "
        last_sep = ", y " if spanish else ", and "
        body = sep.join(shown[:-1]) + last_sep + shown[-1]
    extra = ""
    if len(names) > len(shown):
        if spanish:
            extra = f", entre {len(names)} productos mencionados en el expediente"
        else:
            extra = f", among {len(names)} products mentioned in the record"
    if spanish:
        return _ensure_sentence(f"Medicación relevante: {body}{extra}")
    return _ensure_sentence(f"Relevant medications include {body}{extra}")


def clinical_workspace_from_hints(hints: dict[str, Any]) -> ExtractionClinicalInfo:
    """Build temporary clinical workspace fields used for heuristic fallback only."""
    entries = hints.get("visit_blocks") or []
    diagnoses = hints.get("diagnosis_hints") or []
    meds = hints.get("medication_hints") or []
    chief = entries[-1].get("summary") if entries else None
    return ExtractionClinicalInfo(
        chief_complaint=chief,
        diagnosis="; ".join(diagnoses) if diagnoses else None,
        medications=[Medication(**m) for m in meds],
        history_entries=[HistoryEntry(**e) for e in entries],
    )


def has_clinical_hints(hints: dict[str, Any], body: str = "") -> bool:
    """Whether the document likely has clinical content worth summarizing."""
    if (
        hints.get("visit_blocks")
        or hints.get("diagnosis_hints")
        or hints.get("medication_hints")
    ):
        return True
    from app.adapters.text_hints import clinical_focus_text

    return len(clinical_focus_text(body).strip()) > 100


def has_clinical_content(record: ExtractionRecord) -> bool:
    """Whether heuristic workspace fields can produce a summary."""
    clinical = record.clinical
    if (
        clinical.diagnosis
        or clinical.chief_complaint
        or clinical.examination
        or clinical.treatment
        or clinical.medications
        or clinical.history_entries
    ):
        return True
    return bool(clinical.notes and not _is_generic_note(clinical.notes))


def clinical_summary_user_prompt(
    body: str,
    *,
    language_hint: str | None = None,
    max_source_chars: int = 12000,
) -> str:
    from app.adapters.text_hints import clinical_focus_text

    source = clinical_focus_text(body, max_chars=max_source_chars)
    parts = [
        "Write a readable clinical summary for a veterinarian.",
        "Base the summary on the source text below.",
    ]
    if language_hint:
        parts.append(f"Document language hint: {language_hint}")
    parts.append(
        "SOURCE TEXT (clinical body; exclude pet/owner demographics):\n" + source
    )
    return "\n\n".join(parts)


def finalize_clinical_summary_from_hints(
    record: ExtractionRecord, hints: dict[str, Any]
) -> ExtractionRecord:
    """Build heuristic workspace from hints and set clinical.history (fallback path)."""
    data = record.model_dump()
    data["clinical"] = clinical_workspace_from_hints(hints).model_dump()
    return finalize_clinical_summary(ExtractionRecord.model_validate(data))


def build_heuristic_clinical_summary(record: ExtractionRecord) -> str:
    """Readable fallback summary from structured clinical fields (not pet/owner)."""
    clinical = record.clinical
    spanish = _is_spanish(record)
    med_names = _medication_names(clinical.medications)
    paragraphs: list[str] = []

    overview: list[str] = []
    if clinical.diagnosis:
        diagnoses = _normalize_list_field(clinical.diagnosis)
        if spanish:
            overview.append(f"El expediente documenta {diagnoses}.")
        else:
            overview.append(f"The record documents {diagnoses}.")

    chief = _chief_complaint_for_summary(clinical, med_names)
    if chief:
        if spanish:
            overview.append(_ensure_sentence(f"Motivo de consulta reciente: {chief}"))
        else:
            overview.append(_ensure_sentence(f"Recent concern: {chief}"))

    if clinical.examination:
        if spanish:
            overview.append(
                _ensure_sentence(
                    f"En la exploración se observa {clinical.examination}"
                )
            )
        else:
            overview.append(
                _ensure_sentence(f"Examination findings include {clinical.examination}")
            )
    if overview:
        paragraphs.append(" ".join(overview))

    visit_parts: list[str] = []
    for entry in clinical.history_entries or []:
        summary = _sanitize_summary_fragment(
            (entry.summary or "").strip().rstrip("."), med_names
        )
        if not summary:
            continue
        date = (entry.date or "").strip()
        if date:
            visit_parts.append(f"el {date}, {summary}" if spanish else f"on {date}, {summary}")
        else:
            visit_parts.append(summary)

    if visit_parts:
        if len(visit_parts) == 1:
            if spanish:
                paragraphs.append(
                    _ensure_sentence(f"En el historial de visitas se anota que {visit_parts[0]}")
                )
            else:
                paragraphs.append(
                    _ensure_sentence(f"Visit history notes that {visit_parts[0]}")
                )
        else:
            joined = "; ".join(visit_parts)
            if spanish:
                paragraphs.append(
                    _ensure_sentence(
                        f"A lo largo de las visitas, el expediente refiere {joined}"
                    )
                )
            else:
                paragraphs.append(
                    _ensure_sentence(f"Across visits, the record notes {joined}")
                )

    if clinical.treatment:
        if spanish:
            paragraphs.append(
                _ensure_sentence(f"Tratamiento y manejo: {clinical.treatment}")
            )
        else:
            paragraphs.append(
                _ensure_sentence(f"Treatment and management: {clinical.treatment}")
            )

    med_paragraph = _format_medications_paragraph(clinical.medications, spanish=spanish)
    if med_paragraph:
        paragraphs.append(med_paragraph)

    if clinical.notes and not _is_generic_note(clinical.notes):
        sanitized_note = _sanitize_summary_fragment(clinical.notes, med_names)
        if sanitized_note:
            paragraphs.append(_ensure_sentence(sanitized_note))

    visit = record.visit
    if visit.veterinarian and str(visit.veterinarian).strip():
        vet = visit.veterinarian.strip()
        if spanish:
            paragraphs.append(_ensure_sentence(f"Veterinario responsable: {vet}"))
        else:
            paragraphs.append(_ensure_sentence(f"Attending veterinarian: {vet}"))

    if not paragraphs and visit.clinic_name and str(visit.clinic_name).strip():
        clinic = visit.clinic_name.strip()
        if spanish:
            paragraphs.append(
                _ensure_sentence(
                    f"Documentación clínica de {clinic} con detalle estructurado limitado"
                )
            )
        else:
            paragraphs.append(
                _ensure_sentence(
                    f"Clinical documentation from {clinic} with limited structured detail extracted"
                )
            )

    return truncate_clinical_summary("\n\n".join(paragraphs))


def with_clinical_summary_source(
    record: ExtractionRecord, source: Literal["llm", "heuristic_fallback", "heuristic"]
) -> ExtractionRecord:
    data = record.model_dump()
    data["meta"]["clinical_summary_source"] = source
    return ExtractionRecord.model_validate(data)


def finalize_clinical_summary(record: ExtractionRecord) -> ExtractionRecord:
    """Set clinical.history from heuristic clinical content (fallback when LLM unavailable)."""
    summary = build_heuristic_clinical_summary(record)
    data = record.model_dump()
    data["clinical"]["history"] = summary or None
    return ExtractionRecord.model_validate(data)
