"""Clinical summary (clinical.history) generated at extraction time."""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field

from app.domain.models import ClinicalInfo, MedicalRecord, Medication

CLINICAL_SUMMARY_MAX = 2000


class ClinicalSummaryPolish(BaseModel):
    """Single-field output for optional LLM polish of clinical.history."""

    summary: str | None = Field(
        default=None,
        description="Readable clinical summary excluding pet/owner demographics, max 2000 characters.",
    )


_GENERIC_NOTES = (
    "structured mainly from layout/visit heuristics",
    "clinical fields filled from document heuristics",
    "llm narrative skipped",
    "documento en español",
    "historial multi-visita",
    "multi-visita",
)

_WEIGHT_RE = re.compile(r"\b(?:peso|weight)\s*[:\s]*[\d.,]+\s*kg\b", re.IGNORECASE)
_CHIP_RE = re.compile(r"\b\d{9,15}\b")


def _is_spanish(record: MedicalRecord) -> bool:
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
    clinical: ClinicalInfo, medication_names: list[str]
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

CLINICAL_SUMMARY_POLISH_PROMPT = """You write clinical summaries for veterinarians reviewing imported PDF records.

Return JSON with a single `summary` field containing readable prose for a human reader.

Requirements:
- Maximum 2000 characters in `summary`.
- Write 1–4 short paragraphs with complete sentences (not bullet fragments or label dumps).
- Highlight the most important clinical information across the whole document.
- Include when present: key diagnoses/problems, visit timeline with dates where useful, examination findings, treatments/plans, and a brief mention of relevant medications (drug names only — not a full pharmacy list).
- Use the document language (Spanish or English) when clear from the source.
- Use ONLY facts from the structured facts and source text. Never invent diagnoses, drugs, or dates.

Forbidden in the summary:
- Pet demographics (name, species, breed, sex, date of birth, microchip).
- Owner/client identity or contact details (name, phone, email, address).
- Generic headers like "Historial con N visitas desde…" unless clinically meaningful.
"""


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


def has_clinical_content(record: MedicalRecord, hints: dict[str, Any]) -> bool:
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
    if clinical.notes and not _is_generic_note(clinical.notes):
        return True
    return bool(
        hints.get("visit_blocks")
        or hints.get("diagnosis_hints")
        or hints.get("medication_hints")
    )


def clinical_facts_payload(record: MedicalRecord) -> dict[str, Any]:
    clinical = record.clinical
    notes = clinical.notes
    if _is_generic_note(notes):
        notes = None
    return {
        "diagnosis": clinical.diagnosis,
        "chief_complaint": clinical.chief_complaint,
        "examination": clinical.examination,
        "treatment": clinical.treatment,
        "notes": notes,
        "medications": _medication_names(clinical.medications),
        "history_entries": [
            {"date": entry.date, "summary": entry.summary}
            for entry in clinical.history_entries or []
            if entry.date or entry.summary
        ],
        "visit_date": record.visit.date,
        "veterinarian": record.visit.veterinarian,
    }


def build_heuristic_clinical_summary(record: MedicalRecord) -> str:
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


def summary_polish_user_prompt(
    baseline: str,
    hints: dict[str, Any],
    body: str,
    record: MedicalRecord,
    max_source_chars: int = 6000,
) -> str:
    from app.adapters.text_hints import clinical_focus_text

    source = clinical_focus_text(body, max_chars=max_source_chars)
    facts = clinical_facts_payload(record)
    hint_block = {
        "diagnosis_hints": hints.get("diagnosis_hints") or [],
        "medication_hints": [
            m.get("name") for m in (hints.get("medication_hints") or []) if m.get("name")
        ],
        "visit_blocks": (hints.get("visit_blocks") or [])[-12:],
    }
    baseline_block = baseline.strip() or "(no baseline — synthesize from facts and text)"
    return (
        "Write a readable clinical summary for a veterinarian.\n\n"
        f"Structured facts:\n{json.dumps(facts, ensure_ascii=False, indent=2)}\n\n"
        f"Extraction hints:\n{json.dumps(hint_block, ensure_ascii=False, indent=2)}\n\n"
        f"Baseline draft (improve into clear prose):\n{baseline_block}\n\n"
        "SOURCE TEXT (clinical body; exclude pet/owner header columns):\n"
        f"{source}"
    )


def finalize_clinical_summary(record: MedicalRecord) -> MedicalRecord:
    """Set clinical.history from structured clinical content (extraction / re-process only)."""
    summary = build_heuristic_clinical_summary(record)
    data = record.model_dump()
    data["clinical"]["history"] = summary or None
    return MedicalRecord.model_validate(data)
