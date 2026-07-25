"""LLM adapters for structuring medical records."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.domain.models import MedicalRecord, MetaInfo


SYSTEM_PROMPT = """You extract veterinary medical record fields from document text.
Return ONLY data grounded in the text. Use null for unknown fields.
Do not invent diagnoses, medications, names, or dates.
List missing important fields in meta.missing_fields.
Set meta.extraction_confidence to low, medium, or high based on text clarity.
"""


class MedicalRecordStructurer(ABC):
    @abstractmethod
    def structure(self, raw_text: str) -> MedicalRecord:
        raise NotImplementedError

    @abstractmethod
    def health(self) -> str:
        """Return available | unavailable | skipped."""
        raise NotImplementedError


class OllamaStructurer(MedicalRecordStructurer):
    def __init__(
        self,
        *,
        base_url: str,
        model: str,
        timeout_seconds: float = 120.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def health(self) -> str:
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/api/tags")
                response.raise_for_status()
            return "available"
        except Exception:
            return "unavailable"

    def structure(self, raw_text: str) -> MedicalRecord:
        if not raw_text.strip():
            return MedicalRecord(
                meta=MetaInfo(
                    extraction_confidence="low",
                    missing_fields=["raw_text"],
                )
            )

        schema = MedicalRecord.model_json_schema()
        payload: dict[str, Any] = {
            "model": self.model,
            "stream": False,
            "format": schema,
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Extract a structured veterinary medical record as JSON "
                        "matching the schema.\n\nDOCUMENT TEXT:\n"
                        f"{raw_text[:20000]}"
                    ),
                },
            ],
        }

        try:
            with httpx.Client(timeout=self.timeout_seconds) as client:
                response = client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                )
                response.raise_for_status()
                body = response.json()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        content = (body.get("message") or {}).get("content")
        if not content:
            raise RuntimeError("Ollama returned empty content")

        return MedicalRecord.model_validate_json(content)


class FakeLLMStructurer(MedicalRecordStructurer):
    """Deterministic structurer for tests and demos without Ollama."""

    def health(self) -> str:
        return "skipped"

    def structure(self, raw_text: str) -> MedicalRecord:
        lower = raw_text.lower()
        pet_name = "Buddy" if "buddy" in lower else "Unknown Pet"
        species = "Canine" if "dog" in lower or "canine" in lower else None
        diagnosis = None
        if "otitis" in lower:
            diagnosis = "Otitis externa"
        elif "vaccination" in lower:
            diagnosis = "Routine vaccination"

        return MedicalRecord.model_validate(
            {
                "pet": {
                    "name": pet_name,
                    "species": species or "Unknown",
                    "breed": "Labrador Retriever" if "labrador" in lower else None,
                    "sex": "Male" if "male" in lower else None,
                    "date_of_birth": "2020-03-15" if "2020-03-15" in raw_text else None,
                },
                "owner": {
                    "name": "Jane Doe" if "jane doe" in lower else None,
                    "phone": "+1-555-0100" if "555-0100" in raw_text else None,
                    "email": "jane@example.com" if "jane@example.com" in lower else None,
                },
                "visit": {
                    "date": "2024-06-10" if "2024-06-10" in raw_text else None,
                    "clinic_name": "Sunshine Vet Clinic"
                    if "sunshine" in lower
                    else None,
                    "veterinarian": "Dr. Smith" if "dr. smith" in lower else None,
                },
                "clinical": {
                    "chief_complaint": "Left ear scratching and head shaking"
                    if "ear" in lower
                    else None,
                    "history": "Symptoms for 3 days" if "3 days" in lower else None,
                    "examination": "Mild erythema in left ear canal"
                    if "erythema" in lower
                    else None,
                    "diagnosis": diagnosis,
                    "treatment": "Topical ear medication"
                    if "topical" in lower
                    else None,
                    "medications": [
                        {
                            "name": "Otomax",
                            "dosage": "4 drops",
                            "frequency": "Twice daily for 7 days",
                        }
                    ]
                    if "otomax" in lower
                    else [],
                    "notes": "Follow up in 1 week" if "follow up" in lower else None,
                },
                "meta": {
                    "source_language": "en",
                    "extraction_confidence": "high" if raw_text.strip() else "low",
                    "missing_fields": [],
                },
            }
        )


def build_structurer(
    *,
    provider: str,
    base_url: str,
    model: str,
    timeout_seconds: float,
) -> MedicalRecordStructurer:
    if provider == "fake":
        return FakeLLMStructurer()
    if provider == "ollama":
        return OllamaStructurer(
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds,
        )
    raise ValueError(f"Unknown LLM provider: {provider}")
