# Scope — Lean MVP

## In scope

- Single-user web app (no authentication)
- PDF upload only (text-based / digitally generated PDFs)
- Text extraction with **pdfplumber**
- Structured extraction via a **hybrid pipeline**:
  - layout/visit **heuristics** (Spanish/English clinic headers — including **inline compound lines** such as `ALYA - Nacimiento: DATE` and `Hembra Estado: …` (sex only); **label-free species/breed lines** such as `CANINA - YORKSHIRE TERRIER` or standalone `Canino` without `Especie:` / `Raza:` labels; dated historial blocks; diagnosis/med hints)
  - optional **Ollama** structured outputs (`qwen2.5:7b` by default) when heuristics are weak or `LLM_CLINICAL_MODE=llm`
  - **FakeLLM** adapter for tests and demos without Ollama
- Persist original file, raw text, and structured JSON (SQLite + filesystem)
- React UI: upload, list, on-demand extracted-text preview, structured record (read-only by default; edit mode for Pet / Owner / clinical resume / medications / Meta), **processing-state polling**
- REST API (FastAPI)
- **Async processing by default** (`PROCESSING_MODE=async`): upload returns immediately; extract + structure run in a background task; client polls record status
- Docker Compose for API + frontend
- Specs, architecture docs, install instructions, future-work notes

## Out of scope (v1)

- Word, images, and other non-PDF formats
- OCR for scanned/image-only PDFs
- Multi-user auth, roles, clinic tenancy
- Dedicated job queues / workers (Redis, Celery, RQ, etc.) — in-process `BackgroundTasks` only
- Cloud LLM APIs (paid or remote)
- PDF visual page viewer (optional later; text preview is enough)
- Real-time collaboration / websockets
- Production hardening (rate limits, audit logs, HIPAA/GDPR compliance program)

## Constraints

- Free and open-source libraries only
- Prefer permissive licenses (MIT/BSD/Apache); avoid AGPL dependencies
- Ollama runs on the host when LLM mode needs it (documented)
- **Failure policy:** if heuristics can produce a usable record, LLM timeout/unavailability MUST NOT force `status=failed` (see `specs/architecture.md` failure matrix)
- Document size/timeout limits via env (`MAX_UPLOAD_BYTES`, `OLLAMA_TIMEOUT_SECONDS`, etc.)
