"""Domain models for veterinary medical records."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RecordStatus(str, Enum):
    processing = "processing"
    completed = "completed"
    failed = "failed"


class PetInfo(BaseModel):
    name: str | None = Field(
        default=None, description="Pet given name (Nombre). Not the owner name."
    )
    species: str | None = Field(
        default=None,
        description="Species / Especie, e.g. Canino, Felino, dog, cat.",
    )
    breed: str | None = Field(default=None, description="Breed / Raza.")
    sex: str | None = Field(
        default=None, description="Sex / Sexo, e.g. M, H, Male, Female."
    )
    date_of_birth: str | None = Field(
        default=None,
        description="Date of birth / F/Nto / F.Nac. Keep original or ISO if clear.",
    )
    microchip: str | None = Field(
        default=None, description="Microchip number / Nº Chip if present."
    )
    weight: str | None = Field(
        default=None,
        description="Most recent weight with unit if available, e.g. 29.6kg.",
    )
    coat_color: str | None = Field(
        default=None, description="Coat / Capa / color if present."
    )


class OwnerInfo(BaseModel):
    name: str | None = Field(
        default=None,
        description="Client/owner full name (Datos del Cliente / Nombre del cliente).",
    )
    phone: str | None = Field(default=None, description="Phone if present.")
    email: str | None = Field(default=None, description="Email if present.")
    address: str | None = Field(
        default=None,
        description="Postal address lines for the owner/client if present.",
    )


class VisitInfo(BaseModel):
    date: str | None = Field(
        default=None,
        description="Most recent visit date found in the document.",
    )
    clinic_name: str | None = Field(
        default=None,
        description="Clinic/centre name or brand if present (e.g. Parque Oeste, Kivet).",
    )
    veterinarian: str | None = Field(
        default=None, description="Veterinarian name if explicitly stated."
    )


class Medication(BaseModel):
    name: str | None = Field(default=None, description="Medication or product name.")
    dosage: str | None = Field(default=None, description="Dose amount if stated.")
    frequency: str | None = Field(
        default=None, description="Frequency / duration if stated."
    )


class HistoryEntry(BaseModel):
    date: str | None = Field(default=None, description="Visit date for this entry.")
    summary: str | None = Field(
        default=None,
        description="Short factual summary of what happened on that visit.",
    )


class ClinicalInfo(BaseModel):
    chief_complaint: str | None = Field(
        default=None,
        description="Main reason for the most recent or dominant consultation.",
    )
    history: str | None = Field(
        default=None,
        description="Concise overall clinical history narrative (not every visit).",
    )
    examination: str | None = Field(
        default=None,
        description="Key examination findings (latest and clinically important).",
    )
    diagnosis: str | None = Field(
        default=None,
        description="Main diagnoses / conditions mentioned (comma-separated if several).",
    )
    treatment: str | None = Field(
        default=None,
        description="Key treatments / plans, especially recent or ongoing.",
    )
    medications: list[Medication] = Field(
        default_factory=list,
        description="Important medications from recent visits (max ~8).",
    )
    history_entries: list[HistoryEntry] = Field(
        default_factory=list,
        description="Up to 12 dated visit highlights from a multi-visit history.",
    )
    notes: str | None = Field(
        default=None, description="Other relevant notes for the clinician."
    )


class MetaInfo(BaseModel):
    source_language: str | None = Field(
        default=None,
        description="Primary document language as ISO 639-1 code, e.g. es, en, fr.",
    )
    extraction_confidence: Literal["low", "medium", "high"] = Field(
        default="low",
        description="Confidence in the extraction quality.",
    )
    missing_fields: list[str] = Field(
        default_factory=list,
        description="Important fields that could not be found in the text.",
    )


class MedicalRecord(BaseModel):
    pet: PetInfo = Field(default_factory=PetInfo)
    owner: OwnerInfo = Field(default_factory=OwnerInfo)
    visit: VisitInfo = Field(default_factory=VisitInfo)
    clinical: ClinicalInfo = Field(default_factory=ClinicalInfo)
    meta: MetaInfo = Field(default_factory=MetaInfo)


class RecordSummary(BaseModel):
    id: str
    original_filename: str
    status: RecordStatus
    created_at: datetime
    updated_at: datetime
    pet_name: str | None = None


class RecordResponse(BaseModel):
    id: str
    original_filename: str
    content_type: str
    status: RecordStatus
    error_message: str | None = None
    raw_text: str | None = None
    structured_data: MedicalRecord | None = None
    created_at: datetime
    updated_at: datetime


class RecordPatch(BaseModel):
    structured_data: MedicalRecord


class HealthResponse(BaseModel):
    status: str
    ollama: Literal["available", "unavailable", "skipped"]
    model: str


def new_record_id() -> str:
    return str(uuid4())
