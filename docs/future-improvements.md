# Future Improvements

- **OCR** for scanned PDFs and image-only Word content (Tesseract or Docling OCR pipeline)
- **More formats:** legacy `.doc`, images (JPEG/PNG), RTF, etc.
- **Durable job queue** (Redis/Celery/RQ/etc.) to replace in-process `BackgroundTasks` for multi-instance deployments
- **Clinic-specific templates** and richer multilingual prompt packs beyond ES/EN heuristics
- **Postgres + object storage** for multi-user deployments
- **AuthN/AuthZ** and audit trail for clinical compliance
- **Document page preview** (PDF or Word visual viewer) alongside extracted text
- **Evaluation set** of anonymized records to measure extraction quality
- **Expand pet breed catalog** (`adapters/pet_breed_catalog.py`) for mixed breeds, regional names, and breeds missing from the finite v1 list (today unknown breeds are omitted on extraction, not stored)
- Optional stronger/faster models when hardware allows; automatic model routing by document length
- **Push transport** (SSE/WebSocket) for progress events — v1 already exposes percent and step messages via HTTP polling on `RecordResponse.processing`; push would reduce poll frequency and enable multi-tab live updates
- **More site UI languages** beyond English and Spanish (v1 toggle is EN/ES only)
- **List UI file-type indicator** (PDF vs Word icon/badge; v1 list shows filename only)
