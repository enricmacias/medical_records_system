"""Domain models for veterinary medical records."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from app.domain.processing import ProcessingProgress


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
        description="Species / Especie — canonical Dog or Cat when normalized; e.g. Canino, Felino.",
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


class ClinicalInfo(BaseModel):
    model_config = ConfigDict(extra="ignore")

    history: str | None = Field(
        default=None,
        description="Clinical summary — readable prose generated at extraction (max 2000 chars).",
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
    model_config = ConfigDict(extra="ignore")

    pet: PetInfo = Field(default_factory=PetInfo)
    owner: OwnerInfo = Field(default_factory=OwnerInfo)
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
    processing: ProcessingProgress | None = Field(
        default=None,
        description="Progress details while status is processing; null when completed or failed.",
    )
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
