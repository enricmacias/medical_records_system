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
    name: str | None = None
    species: str | None = None
    breed: str | None = None
    sex: str | None = None
    date_of_birth: str | None = None


class OwnerInfo(BaseModel):
    name: str | None = None
    phone: str | None = None
    email: str | None = None


class VisitInfo(BaseModel):
    date: str | None = None
    clinic_name: str | None = None
    veterinarian: str | None = None


class Medication(BaseModel):
    name: str | None = None
    dosage: str | None = None
    frequency: str | None = None


class ClinicalInfo(BaseModel):
    chief_complaint: str | None = None
    history: str | None = None
    examination: str | None = None
    diagnosis: str | None = None
    treatment: str | None = None
    medications: list[Medication] = Field(default_factory=list)
    notes: str | None = None


class MetaInfo(BaseModel):
    source_language: str | None = None
    extraction_confidence: Literal["low", "medium", "high"] = "low"
    missing_fields: list[str] = Field(default_factory=list)


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
