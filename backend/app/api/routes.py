"""HTTP routes for medical records."""

from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from app.config import Settings
from app.dependencies import get_app_settings, get_record_service, get_store, get_structurer
from app.domain.models import (
    HealthResponse,
    RecordPatch,
    RecordResponse,
    RecordSummary,
)
from app.services.records import RecordService
from app.services.store import RecordStore

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
def health(
    settings: Settings = Depends(get_app_settings),
) -> HealthResponse:
    structurer = get_structurer()
    return HealthResponse(
        status="ok",
        ollama=structurer.health(),  # type: ignore[arg-type]
        model=settings.ollama_model,
    )


@router.post("/records", response_model=RecordResponse, status_code=201)
async def create_record(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    service: RecordService = Depends(get_record_service),
) -> RecordResponse:
    try:
        record = await service.create_from_upload(file)
    except ValueError as exc:
        message = str(exc)
        if "maximum size" in message:
            raise HTTPException(status_code=413, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc

    # Async mode returns while status=processing; finish LLM work in background.
    if (
        service.processing_mode != "sync"
        and record.status.value == "processing"
    ):
        background_tasks.add_task(service.process_record, record.id)

    return record


@router.get("/records")
def list_records(store: RecordStore = Depends(get_store)) -> dict[str, list[RecordSummary]]:
    return {"items": store.list_records()}


@router.get("/records/{record_id}", response_model=RecordResponse)
def get_record(
    record_id: str, store: RecordStore = Depends(get_store)
) -> RecordResponse:
    try:
        return store.get(record_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Record not found") from exc


@router.patch("/records/{record_id}", response_model=RecordResponse)
def patch_record(
    record_id: str,
    body: RecordPatch,
    store: RecordStore = Depends(get_store),
) -> RecordResponse:
    try:
        return store.update_structured_data(record_id, body.structured_data)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Record not found") from exc


@router.get("/records/{record_id}/file")
def download_file(
    record_id: str, store: RecordStore = Depends(get_store)
) -> FileResponse:
    try:
        record = store.get(record_id)
        path = Path(store.get_stored_path(record_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Record not found") from exc

    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path,
        media_type=record.content_type,
        filename=record.original_filename,
    )
