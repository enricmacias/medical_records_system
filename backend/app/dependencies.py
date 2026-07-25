"""Dependency wiring."""

from functools import lru_cache
from pathlib import Path

from app.adapters.llm import MedicalRecordStructurer, build_structurer
from app.adapters.pdf_extractor import PdfTextExtractor, PdfplumberExtractor
from app.config import Settings, get_settings
from app.services.records import RecordService
from app.services.store import RecordStore


@lru_cache
def get_store() -> RecordStore:
    settings = get_settings()
    return RecordStore(settings.database_url)


@lru_cache
def get_extractor() -> PdfTextExtractor:
    return PdfplumberExtractor()


@lru_cache
def get_structurer() -> MedicalRecordStructurer:
    settings = get_settings()
    return build_structurer(
        provider=settings.llm_provider,
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
    )


def get_record_service() -> RecordService:
    settings = get_settings()
    return RecordService(
        store=get_store(),
        extractor=get_extractor(),
        structurer=get_structurer(),
        upload_dir=Path(settings.upload_dir),
        max_upload_bytes=settings.max_upload_bytes,
    )


def get_app_settings() -> Settings:
    return get_settings()
