"""Dependency wiring."""

from functools import lru_cache
from pathlib import Path

from app.adapters.llm import MedicalRecordStructurer, build_structurer
from app.adapters.document_extractor import CompositeDocumentExtractor, DocumentTextExtractor
from app.config import Settings, get_settings
from app.services.records import RecordService
from app.services.store import RecordStore


@lru_cache
def get_store() -> RecordStore:
    settings = get_settings()
    return RecordStore(settings.database_url)


@lru_cache
def get_extractor() -> DocumentTextExtractor:
    return CompositeDocumentExtractor()


@lru_cache
def get_structurer() -> MedicalRecordStructurer:
    settings = get_settings()
    return build_structurer(
        provider=settings.llm_provider,
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        timeout_seconds=settings.ollama_timeout_seconds,
        skip_demographics_when_hinted=settings.llm_skip_demographics_when_hinted,
        clinical_mode=settings.llm_clinical_mode,
        num_predict=settings.ollama_num_predict,
        num_ctx=settings.ollama_num_ctx,
    )


def get_record_service() -> RecordService:
    settings = get_settings()
    return RecordService(
        store=get_store(),
        extractor=get_extractor(),
        structurer=get_structurer(),
        upload_dir=Path(settings.upload_dir),
        max_upload_bytes=settings.max_upload_bytes,
        processing_mode=settings.processing_mode,
    )


def get_app_settings() -> Settings:
    return get_settings()
