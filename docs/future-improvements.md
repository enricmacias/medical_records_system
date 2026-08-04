# Future Improvements

- **OCR** for scanned PDFs and image-only Word content (Tesseract or Docling OCR pipeline)
- **More formats:** legacy `.doc`, images (JPEG/PNG), RTF, etc.
- **Durable job queue** (Redis/Celery/RQ/etc.) to replace in-process `BackgroundTasks` for multi-instance deployments
- **Clinic-specific templates** and richer multilingual prompt packs beyond ES/EN heuristics
- **Improve pet name detection** — heuristics and demographics LLM still miss names when `mascota` / `patient` / `paciente` appear heavily in historial prose (not just headers), or when the pet has an unusual or uncommon proper name; ranked hints can still skip the LLM when a wrong-but-valid name is chosen
- **Improve demographic extraction from Word tables** — `pet.breed`, `pet.date_of_birth`, `owner.phone`, `owner.email`, and `owner.address` are often missed when values live in table cells rather than plain label lines (v1 flattens rows to `cell | cell | cell` without cell-aware label/value pairing)
- **Richer clinical summary** — improve `clinical.history` generation (heuristic baseline and/or LLM polish) to produce a more polished, readable résumé of the full clinical record
- **Postgres + object storage** for multi-user deployments
- **AuthN/AuthZ** and audit trail for clinical compliance
- **Expand pet breed catalog** (`adapters/pet_breed_catalog.py`) for mixed breeds, regional names, and breeds missing from the finite v1 list (today unknown breeds are omitted on extraction, not stored)
- Optional stronger/faster models when hardware allows; automatic model routing by document length
- **Push transport** (SSE/WebSocket) for progress events — v1 already exposes percent and step messages via HTTP polling on `RecordResponse.processing`; push would reduce poll frequency and enable multi-tab live updates
- **More site UI languages** beyond English and Spanish (v1 toggle is EN/ES only)
- **List UI file-type indicator** (PDF vs Word icon/badge; v1 list shows filename only)
