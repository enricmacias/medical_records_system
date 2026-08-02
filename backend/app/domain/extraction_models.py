"""Full extraction workspace used during structuring; not persisted on the record."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.domain.models import ClinicalInfo, MedicalRecord, MetaInfo, OwnerInfo, PetInfo


class VisitInfo(BaseModel):
    date: str | None = Field(
        default=None,
        description="Most recent visit date found in the document.",
    )
    clinic_name: str | None = Field(
        default=None,
        description="Clinic/centre name or brand if present.",
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


class ExtractionClinicalInfo(BaseModel):
    chief_complaint: str | None = None
    history: str | None = None
    examination: str | None = None
    diagnosis: str | None = None
    treatment: str | None = None
    medications: list[Medication] = Field(default_factory=list)
    history_entries: list[HistoryEntry] = Field(default_factory=list)
    notes: str | None = None


class ExtractionRecord(BaseModel):
    """In-memory record while extracting; slimmed before persistence."""

    pet: PetInfo = Field(default_factory=PetInfo)
    owner: OwnerInfo = Field(default_factory=OwnerInfo)
    visit: VisitInfo = Field(default_factory=VisitInfo)
    clinical: ExtractionClinicalInfo = Field(default_factory=ExtractionClinicalInfo)
    meta: MetaInfo = Field(default_factory=MetaInfo)


PERSISTED_MISSING_PATHS = (
    "pet.name",
    "pet.species",
    "pet.breed",
    "owner.name",
    "clinical.history",
)


def missing_fields_for_persisted(record: ExtractionRecord) -> list[str]:
    missing: list[str] = []
    data = record.model_dump()
    for path in PERSISTED_MISSING_PATHS:
        section, field = path.split(".")
        value = data.get(section, {}).get(field)
        if value in (None, "", []):
            missing.append(path)
    return missing


def to_persisted_record(record: ExtractionRecord) -> MedicalRecord:
    meta = record.meta.model_copy(
        update={"missing_fields": missing_fields_for_persisted(record)}
    )
    return MedicalRecord(
        pet=record.pet,
        owner=record.owner,
        clinical=ClinicalInfo(history=record.clinical.history),
        meta=meta,
    )
