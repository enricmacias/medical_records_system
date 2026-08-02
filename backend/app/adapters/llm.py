"""LLM adapters for structuring medical records."""

from __future__ import annotations

import copy
import json
from abc import ABC, abstractmethod
from typing import Any, Callable

import httpx
from pydantic import BaseModel, Field

from app.domain.processing import ProcessingProgress

from app.adapters.clinical_summary import (
    CLINICAL_SUMMARY_POLISH_PROMPT,
    ClinicalSummaryPolish,
    finalize_clinical_summary,
    has_clinical_content,
    summary_polish_user_prompt,
    truncate_clinical_summary,
)
from app.adapters.text_hints import (
    build_layout_hints,
    clinical_focus_text,
    normalize_extracted_text,
    normalize_species_dog_cat,
    infer_species_from_text,
    split_for_long_document,
)
from app.domain.extraction_models import (
    ExtractionClinicalInfo,
    ExtractionRecord,
    HistoryEntry,
    Medication,
    VisitInfo,
    to_persisted_record,
)
from app.domain.models import MedicalRecord, MetaInfo, OwnerInfo, PetInfo


SYSTEM_PROMPT = """You are a veterinary medical-record extraction engine.

Convert messy clinic PDF text (any language, tables, multi-visit histories)
into the provided JSON schema.

Hard rules:
- Use ONLY facts present in the document. Never invent names, diagnoses, drugs, or dates.
- If unknown, use null or [].
- Detect language and set meta.source_language to ISO 639-1 (es, en, fr, ...).
- Two-column headers: "Datos de la Mascota" (left/pet) vs "Datos del Cliente" (right/owner).
  Do NOT put the owner name into pet.name.
- Spanish labels: Nombre, Especie, Raza, F/Nto, Sexo, Nº Chip, Capa.
- For HISTORIAL COMPLETO: fill clinical fields; do not leave them all null when visits exist.
"""

CLINICAL_NARRATIVE_PROMPT = """Write a short clinical summary from the visit snippets.
Return JSON only. Use only facts in the text. Keep each field under 2 sentences.
If unknown, use null. Do not list every visit.
"""


ProgressCallback = Callable[[ProcessingProgress], None]
PartialCallback = Callable[[MedicalRecord], None]


def _emit_progress(
    callback: ProgressCallback | None,
    percent: int,
    step: str,
    message: str,
) -> None:
    if callback:
        callback(ProcessingProgress(percent=percent, step=step, message=message))


class DemographicsBundle(BaseModel):
    pet: PetInfo = Field(default_factory=PetInfo)
    owner: OwnerInfo = Field(default_factory=OwnerInfo)
    visit: VisitInfo = Field(default_factory=VisitInfo)
    meta: MetaInfo = Field(default_factory=MetaInfo)


class ClinicalNarrative(BaseModel):
    """Tiny schema for a fast optional LLM pass."""

    chief_complaint: str | None = Field(default=None)
    history: str | None = Field(default=None)
    examination: str | None = Field(default=None)
    treatment: str | None = Field(default=None)
    notes: str | None = Field(default=None)


def _inline_json_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Inline $refs so Ollama structured outputs handle nested models reliably."""
    defs = schema.get("$defs") or schema.get("definitions") or {}
    root = {k: v for k, v in schema.items() if k not in {"$defs", "definitions"}}

    def resolve(node: Any) -> Any:
        if isinstance(node, dict):
            if "$ref" in node:
                ref = node["$ref"].rsplit("/", 1)[-1]
                return resolve(copy.deepcopy(defs[ref]))
            return {k: resolve(v) for k, v in node.items()}
        if isinstance(node, list):
            return [resolve(v) for v in node]
        return node

    return resolve(root)


def _user_prompt(document_text: str, hints: dict[str, Any]) -> str:
    compact_hints = {
        "language_hint": hints.get("language_hint"),
        "likely_fields": hints.get("likely_fields"),
        "visit_dates_found": (hints.get("visit_dates_found") or [])[-8:],
        "diagnosis_hints": hints.get("diagnosis_hints"),
        "medication_hints": hints.get("medication_hints"),
    }
    return (
        "Extract structured data as JSON matching the schema.\n"
        "Heuristic hints (may be incomplete; prefer the document):\n"
        f"{json.dumps(compact_hints, ensure_ascii=False, indent=2)}\n\n"
        "DOCUMENT TEXT:\n"
        f"{document_text}"
    )


class MedicalRecordStructurer(ABC):
    @abstractmethod
    def structure(
        self,
        raw_text: str,
        *,
        on_progress: ProgressCallback | None = None,
        on_partial: PartialCallback | None = None,
    ) -> MedicalRecord:
        raise NotImplementedError

    @abstractmethod
    def health(self) -> str:
        raise NotImplementedError


class OllamaStructurer(MedicalRecordStructurer):
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float = 90.0,
        skip_demographics_when_hinted: bool = True,
        clinical_mode: str = "hybrid",
        num_predict: int = 384,
        num_ctx: int = 4096,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds
        self.skip_demographics_when_hinted = skip_demographics_when_hinted
        self.clinical_mode = clinical_mode
        self.num_predict = num_predict
        self.num_ctx = num_ctx

    def health(self) -> str:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
            return "available"
        except Exception:
            return "unavailable"

    def structure(
        self,
        raw_text: str,
        *,
        on_progress: ProgressCallback | None = None,
        on_partial: PartialCallback | None = None,
    ) -> MedicalRecord:
        text = normalize_extracted_text(raw_text)
        if not text:
            return MedicalRecord(
                meta=MetaInfo(
                    extraction_confidence="low",
                    missing_fields=["raw_text"],
                )
            )

        _emit_progress(
            on_progress,
            20,
            "demographics",
            "Extracting pet and owner details from the document…",
        )
        hints = build_layout_hints(text)
        _header, body = split_for_long_document(text)

        if self.skip_demographics_when_hinted and self._hints_sufficient(hints):
            demographics = self._demographics_from_hints(hints)
        else:
            try:
                demographics = self._chat_model(
                    model_cls=DemographicsBundle,
                    system=SYSTEM_PROMPT,
                    user=_user_prompt(clinical_focus_text(body, max_chars=3500), hints),
                )
            except Exception:
                demographics = self._demographics_from_hints(hints)

        record = ExtractionRecord(
            pet=demographics.pet,
            owner=demographics.owner,
            visit=demographics.visit,
            clinical=ExtractionClinicalInfo(),
            meta=demographics.meta,
        )
        record = self._apply_demographics_fallbacks(record, hints)
        if on_partial:
            on_partial(to_persisted_record(record))

        _emit_progress(
            on_progress,
            50,
            "clinical_analysis",
            "Reviewing visits, diagnoses, and medications…",
        )
        clinical = self._clinical_from_hints(hints)
        if self._should_call_clinical_llm(hints):
            try:
                narrative = self._chat_model(
                    model_cls=ClinicalNarrative,
                    system=CLINICAL_NARRATIVE_PROMPT,
                    user=self._clinical_user_prompt(hints, body),
                )
                clinical = self._merge_narrative(clinical, narrative)
            except Exception:
                if not clinical.notes:
                    clinical.notes = (
                        "Clinical fields filled from document heuristics; "
                        "LLM narrative skipped (timeout or error)."
                    )

        record = ExtractionRecord(
            pet=record.pet,
            owner=record.owner,
            visit=record.visit,
            clinical=clinical,
            meta=record.meta,
        )
        record = self._apply_fallbacks(record, hints)

        _emit_progress(
            on_progress,
            65,
            "clinical_summary",
            "Writing the clinical summary…",
        )
        record = self._finalize_clinical_summary(
            record, hints, body, on_progress=on_progress
        )
        _emit_progress(
            on_progress,
            95,
            "completing",
            "Saving your structured record…",
        )
        return to_persisted_record(record)

    def _should_call_clinical_llm(self, hints: dict[str, Any]) -> bool:
        mode = (self.clinical_mode or "hybrid").lower()
        if mode == "heuristic":
            return False
        if mode == "llm":
            return True
        # hybrid: only call LLM when heuristics look thin
        return not self._clinical_hints_sufficient(hints)

    @staticmethod
    def _clinical_hints_sufficient(hints: dict[str, Any]) -> bool:
        blocks = hints.get("visit_blocks") or []
        return bool(
            len(blocks) >= 1
            or hints.get("diagnosis_hints")
            or hints.get("medication_hints")
        )

    @staticmethod
    def _clinical_from_hints(hints: dict[str, Any]) -> ExtractionClinicalInfo:
        entries = hints.get("visit_blocks") or []
        diagnoses = hints.get("diagnosis_hints") or []
        meds = hints.get("medication_hints") or []
        history = None
        chief = None
        if entries:
            chief = entries[-1].get("summary")
        return ExtractionClinicalInfo(
            chief_complaint=chief,
            history=history,
            diagnosis="; ".join(diagnoses) if diagnoses else None,
            treatment=None,
            medications=[Medication(**m) for m in meds],
            history_entries=[HistoryEntry(**e) for e in entries],
            notes="Structured mainly from layout/visit heuristics.",
        )

    @staticmethod
    def _merge_narrative(
        clinical: ExtractionClinicalInfo, narrative: ClinicalNarrative
    ) -> ExtractionClinicalInfo:
        data = clinical.model_dump()
        for field in (
            "chief_complaint",
            "history",
            "examination",
            "treatment",
            "notes",
        ):
            value = getattr(narrative, field)
            if value:
                data[field] = value
        return ExtractionClinicalInfo.model_validate(data)

    def _clinical_user_prompt(self, hints: dict[str, Any], body: str) -> str:
        recent = (hints.get("visit_blocks") or [])[-4:]
        if recent:
            snippets = "\n".join(
                f"- {item.get('date')}: {item.get('summary')}" for item in recent
            )
            source = snippets
        else:
            source = clinical_focus_text(body, max_chars=2500)
        return (
            "Summarize the clinical picture.\n"
            f"Known diagnoses: {hints.get('diagnosis_hints')}\n"
            f"Known medications: {[m.get('name') for m in (hints.get('medication_hints') or [])]}\n\n"
            f"TEXT:\n{source}"
        )

    @staticmethod
    def _hints_sufficient(hints: dict[str, Any]) -> bool:
        likely = hints.get("likely_fields") or {}
        return bool(likely.get("pet.name"))

    @staticmethod
    def _demographics_from_hints(hints: dict[str, Any]) -> DemographicsBundle:
        likely = hints.get("likely_fields") or {}
        dates = hints.get("visit_dates_found") or []
        return DemographicsBundle(
            pet=PetInfo(
                name=likely.get("pet.name"),
                species=normalize_species_dog_cat(likely.get("pet.species"))
                or likely.get("pet.species"),
                breed=likely.get("pet.breed"),
                sex=likely.get("pet.sex"),
                date_of_birth=likely.get("pet.date_of_birth"),
                microchip=likely.get("pet.microchip"),
            ),
            owner=OwnerInfo(
                name=likely.get("owner.name"),
                address=likely.get("owner.address"),
            ),
            visit=VisitInfo(
                date=dates[-1] if dates else None,
                clinic_name=likely.get("visit.clinic_name"),
            ),
            meta=MetaInfo(
                source_language=hints.get("language_hint"),
                extraction_confidence="medium",
                missing_fields=[],
            ),
        )

    def _chat_model(
        self,
        *,
        model_cls: type[BaseModel],
        system: str,
        user: str,
    ) -> Any:
        schema = _inline_json_schema(model_cls.model_json_schema())
        payload: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "format": schema,
            "options": {
                "temperature": 0,
                "num_ctx": self.num_ctx,
                "num_predict": self.num_predict,
            },
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(f"{self.base_url}/api/chat", json=payload)
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        content = (body.get("message") or {}).get("content")
        if not content:
            raise RuntimeError("Ollama returned empty content")
        return model_cls.model_validate_json(content)

    @staticmethod
    def _apply_demographics_fallbacks(
        record: ExtractionRecord, hints: dict[str, Any]
    ) -> ExtractionRecord:
        likely = hints.get("likely_fields") or {}
        data = record.model_dump()

        mapping = {
            "pet.name": ("pet", "name"),
            "pet.species": ("pet", "species"),
            "pet.breed": ("pet", "breed"),
            "pet.sex": ("pet", "sex"),
            "pet.date_of_birth": ("pet", "date_of_birth"),
            "pet.microchip": ("pet", "microchip"),
            "owner.name": ("owner", "name"),
            "owner.address": ("owner", "address"),
        }
        for hint_key, path in mapping.items():
            if hint_key not in likely:
                continue
            section, field = path
            if data[section].get(field) in (None, "", []):
                data[section][field] = likely[hint_key]

        if not data["meta"].get("source_language") and hints.get("language_hint"):
            data["meta"]["source_language"] = hints["language_hint"]

        species = normalize_species_dog_cat(data["pet"].get("species"))
        if not species:
            species = normalize_species_dog_cat(likely.get("pet.species"))
        if species:
            data["pet"]["species"] = species

        return ExtractionRecord.model_validate(data)

    @staticmethod
    def _apply_fallbacks(record: ExtractionRecord, hints: dict[str, Any]) -> ExtractionRecord:
        likely = hints.get("likely_fields") or {}
        data = record.model_dump()

        mapping = {
            "pet.name": ("pet", "name"),
            "pet.species": ("pet", "species"),
            "pet.breed": ("pet", "breed"),
            "pet.sex": ("pet", "sex"),
            "pet.date_of_birth": ("pet", "date_of_birth"),
            "pet.microchip": ("pet", "microchip"),
            "owner.name": ("owner", "name"),
            "owner.address": ("owner", "address"),
            "visit.clinic_name": ("visit", "clinic_name"),
        }
        for hint_key, path in mapping.items():
            if hint_key not in likely:
                continue
            section, field = path
            if data[section].get(field) in (None, "", []):
                data[section][field] = likely[hint_key]

        if not data["meta"].get("source_language") and hints.get("language_hint"):
            data["meta"]["source_language"] = hints["language_hint"]

        dates = hints.get("visit_dates_found") or []
        if not data["visit"].get("date") and dates:
            data["visit"]["date"] = dates[-1]

        clinical = data["clinical"]
        if not clinical.get("history_entries"):
            clinical["history_entries"] = hints.get("visit_blocks") or []

        if not clinical.get("diagnosis") and hints.get("diagnosis_hints"):
            clinical["diagnosis"] = "; ".join(hints["diagnosis_hints"])

        if not clinical.get("medications") and hints.get("medication_hints"):
            clinical["medications"] = hints["medication_hints"]

        if not clinical.get("chief_complaint") and clinical.get("history_entries"):
            clinical["chief_complaint"] = clinical["history_entries"][-1].get("summary")

        # Confidence: demographics + some clinical content.
        has_pet = bool(data["pet"].get("name"))
        has_clinical = bool(
            clinical.get("diagnosis")
            or clinical.get("medications")
            or clinical.get("history_entries")
        )
        if has_pet and has_clinical:
            data["meta"]["extraction_confidence"] = "high"
        elif has_pet or has_clinical:
            data["meta"]["extraction_confidence"] = "medium"
        else:
            data["meta"]["extraction_confidence"] = "low"

        missing: list[str] = []
        for path in (
            "pet.name",
            "pet.species",
            "owner.name",
        ):
            section, field = path.split(".")
            if not data[section].get(field):
                missing.append(path)
        data["meta"]["missing_fields"] = missing

        species = normalize_species_dog_cat(data["pet"].get("species"))
        if not species:
            species = normalize_species_dog_cat(likely.get("pet.species"))
        if species:
            data["pet"]["species"] = species

        return ExtractionRecord.model_validate(data)

    def _should_polish_clinical_summary(self, hints: dict[str, Any]) -> bool:
        mode = (self.clinical_mode or "hybrid").lower()
        if mode == "heuristic":
            return False
        if mode == "llm":
            return True
        return self._clinical_hints_sufficient(hints)

    def _finalize_clinical_summary(
        self,
        record: ExtractionRecord,
        hints: dict[str, Any],
        body: str,
        *,
        on_progress: ProgressCallback | None = None,
    ) -> ExtractionRecord:
        baseline_record = finalize_clinical_summary(record)
        if not self._should_polish_clinical_summary(hints):
            return baseline_record
        if not has_clinical_content(baseline_record, hints):
            return baseline_record
        _emit_progress(
            on_progress,
            80,
            "clinical_summary_polish",
            "Polishing the clinical summary with AI (this can take a minute)…",
        )
        baseline = (baseline_record.clinical.history or "").strip()
        try:
            polished = self._chat_model(
                model_cls=ClinicalSummaryPolish,
                system=CLINICAL_SUMMARY_POLISH_PROMPT,
                user=summary_polish_user_prompt(
                    baseline, hints, body, record=baseline_record
                ),
            )
            if polished.summary and polished.summary.strip():
                data = baseline_record.model_dump()
                data["clinical"]["history"] = truncate_clinical_summary(
                    polished.summary.strip()
                )
                return ExtractionRecord.model_validate(data)
        except Exception:
            pass
        return baseline_record


class FakeLLMStructurer(MedicalRecordStructurer):
    """Deterministic structurer for tests and demos without Ollama."""

    def health(self) -> str:
        return "skipped"

    def structure(
        self,
        raw_text: str,
        *,
        on_progress: ProgressCallback | None = None,
        on_partial: PartialCallback | None = None,
    ) -> MedicalRecord:
        text = normalize_extracted_text(raw_text)
        lower = text.lower()
        hints = build_layout_hints(text)
        likely = hints.get("likely_fields") or {}

        _emit_progress(
            on_progress,
            20,
            "demographics",
            "Extracting pet and owner details from the document…",
        )

        if "marley" in lower or likely.get("pet.name") == "MARLEY":
            entries = hints.get("visit_blocks") or [
                {
                    "date": "08/12/19",
                    "summary": "Urgencias por costra/apatía; deshidratación; hospitalización.",
                },
                {
                    "date": "08/04/20",
                    "summary": "Giardia positivo; diarreas; pauta antiparasitaria.",
                },
                {
                    "date": "03/10/20",
                    "summary": "Conjuntivitis folicular; provocación con pienso.",
                },
            ]
            extraction = ExtractionRecord(
                pet=PetInfo(
                    name=likely.get("pet.name") or "MARLEY",
                    species=normalize_species_dog_cat(likely.get("pet.species")) or "Dog",
                    breed=likely.get("pet.breed") or "Labrador Retriever",
                    sex=likely.get("pet.sex") or "M",
                    date_of_birth=likely.get("pet.date_of_birth") or "04/10/19",
                    microchip=likely.get("pet.microchip") or "941000024967769",
                ),
                owner=OwnerInfo(
                    name=likely.get("owner.name") or "BEATRIZ ABARCA",
                    address=likely.get("owner.address"),
                ),
                visit=VisitInfo(
                    date=(hints.get("visit_dates_found") or ["03/10/20"])[-1],
                    clinic_name=likely.get("visit.clinic_name") or "Parque Oeste",
                ),
                clinical=ExtractionClinicalInfo(
                    chief_complaint=entries[-1]["summary"] if entries else None,
                    examination="Exploración variable según visita; heces y ojos frecuentes focos de atención.",
                    diagnosis="; ".join(hints.get("diagnosis_hints") or ["Giardiasis", "Conjuntivitis"]),
                    treatment="Dietas digestivas/hipoalergénicas, antiparasitarios, colirios, probióticos.",
                    medications=[
                        Medication(**m)
                        for m in (
                            hints.get("medication_hints")
                            or [
                                {
                                    "name": "Metronidazol",
                                    "dosage": None,
                                    "frequency": None,
                                },
                                {
                                    "name": "Fortiflora",
                                    "dosage": "1 sobre",
                                    "frequency": "cada 24h",
                                },
                            ]
                        )
                    ],
                    history_entries=[HistoryEntry(**e) for e in entries],
                    notes=None,
                ),
                meta=MetaInfo(
                    source_language="es",
                    extraction_confidence="high",
                    missing_fields=[],
                ),
            )
            return self._finalize_fake_record(
                extraction, on_progress=on_progress, on_partial=on_partial
            )

        diagnosis = None
        if "otitis" in lower:
            diagnosis = "Otitis externa"
        elif "vaccination" in lower or "vacuna" in lower:
            diagnosis = "Routine vaccination"

        extraction = ExtractionRecord(
            pet=PetInfo(
                name="Buddy"
                if "buddy" in lower
                else likely.get("pet.name") or "Unknown Pet",
                species=(
                    "Dog"
                    if ("dog" in lower or "canine" in lower or "canino" in lower)
                    else (
                        "Cat"
                        if ("cat" in lower or "feline" in lower or "felino" in lower)
                        else normalize_species_dog_cat(likely.get("pet.species"))
                    )
                ),
                breed="Labrador Retriever"
                if "labrador" in lower
                else likely.get("pet.breed"),
                sex="Male" if "male" in lower else likely.get("pet.sex"),
                date_of_birth="2020-03-15"
                if "2020-03-15" in text
                else likely.get("pet.date_of_birth"),
                microchip=likely.get("pet.microchip"),
            ),
            owner=OwnerInfo(
                name="Jane Doe"
                if "jane doe" in lower
                else likely.get("owner.name"),
                phone="+1-555-0100" if "555-0100" in text else None,
                email="jane@example.com" if "jane@example.com" in lower else None,
                address=likely.get("owner.address"),
            ),
            visit=VisitInfo(
                date="2024-06-10"
                if "2024-06-10" in text
                else (hints.get("visit_dates_found") or [None])[-1],
                clinic_name="Sunshine Vet Clinic"
                if "sunshine" in lower
                else likely.get("visit.clinic_name"),
                veterinarian="Dr. Smith" if "dr. smith" in lower else None,
            ),
            clinical=ExtractionClinicalInfo(
                chief_complaint="Left ear scratching and head shaking"
                if "ear" in lower
                else ("Symptoms for 3 days" if "3 days" in lower else None),
                examination="Mild erythema in left ear canal"
                if "erythema" in lower
                else None,
                diagnosis=diagnosis,
                treatment="Topical ear medication" if "topical" in lower else None,
                medications=[
                    Medication(
                        name="Otomax",
                        dosage="4 drops",
                        frequency="Twice daily for 7 days",
                    )
                ]
                if "otomax" in lower
                else [],
                history_entries=[
                    HistoryEntry(**e) for e in (hints.get("visit_blocks") or [])
                ],
                notes="Follow up in 1 week" if "follow up" in lower else None,
            ),
            meta=MetaInfo(
                source_language=hints.get("language_hint") or "en",
                extraction_confidence="high" if text else "low",
                missing_fields=[],
            ),
        )
        return self._finalize_fake_record(
            extraction, on_progress=on_progress, on_partial=on_partial
        )

    @staticmethod
    def _finalize_fake_record(
        extraction: ExtractionRecord,
        *,
        on_progress: ProgressCallback | None = None,
        on_partial: PartialCallback | None = None,
    ) -> MedicalRecord:
        if on_partial:
            on_partial(to_persisted_record(extraction))
        _emit_progress(
            on_progress,
            50,
            "clinical_analysis",
            "Reviewing visits, diagnoses, and medications…",
        )
        _emit_progress(
            on_progress,
            65,
            "clinical_summary",
            "Writing the clinical summary…",
        )
        finalized = finalize_clinical_summary(extraction)
        _emit_progress(
            on_progress,
            95,
            "completing",
            "Saving your structured record…",
        )
        return to_persisted_record(finalized)


def build_structurer(
    *,
    provider: str,
    base_url: str,
    model: str,
    timeout_seconds: float,
    skip_demographics_when_hinted: bool = True,
    clinical_mode: str = "hybrid",
    num_predict: int = 384,
    num_ctx: int = 4096,
) -> MedicalRecordStructurer:
    if provider == "fake":
        return FakeLLMStructurer()
    if provider == "ollama":
        return OllamaStructurer(
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds,
            skip_demographics_when_hinted=skip_demographics_when_hinted,
            clinical_mode=clinical_mode,
            num_predict=num_predict,
            num_ctx=num_ctx,
        )
    raise ValueError(f"Unknown LLM provider: {provider}")
