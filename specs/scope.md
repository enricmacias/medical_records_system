# Scope — Lean MVP

## In scope

- Single-user web app (no authentication)
- PDF and Word (.docx) upload (text-based / digitally generated documents)
- Text extraction with **pdfplumber** (PDF) and **python-docx** (Word .docx)
- Structured extraction via a **hybrid pipeline**:
  - layout/visit **heuristics** (Spanish/English clinic headers — including **inline compound lines** such as `ALYA - Nacimiento: DATE` and `Hembra Estado: …` (sex only); **label-free species/breed lines** such as `CANINA - YORKSHIRE TERRIER` or standalone `Canino` without `Especie:` / `Raza:` labels; dated historial blocks; diagnosis/med hints)
  - optional **Ollama** structured outputs (`qwen2.5:7b` by default) for demographics, clinical narrative (weak hints or `llm` mode), and clinical summary polish (strong hints or `llm` mode) per `LLM_CLINICAL_MODE`
  - **FakeLLM** adapter for tests and demos without Ollama (heuristic clinical summary included)
- Persist original file, raw text, and structured JSON (SQLite + filesystem)
- React UI: upload, list, on-demand extracted-text preview, structured record (read-only by default; edit mode for **Pet** and **Owner** only; **Clinical summary** and **Meta** always read-only), **processing-state polling** with **progressive section loading** (pet/owner/meta as soon as ready) and **percent/step progress feedback** for the clinical summary, **site language toggle (English / Español)** with localized UI labels and date display, **confidence UX** (highlight missing and low-confidence fields in the structured form)
- REST API (FastAPI) including `processing` on `RecordResponse` while structuring
- **Async processing by default** (`PROCESSING_MODE=async`): upload returns immediately; extract + structure run in a background task with staged persistence; client polls record status and partial data
- Docker Compose for API + frontend
- Specs, architecture docs, install instructions, future-work notes

## Out of scope (v1)

- Legacy binary Word (**`.doc`** — only **`.docx`** is supported)
- Images and other non-PDF/non-docx formats
- OCR for scanned/image-only PDFs and image-only content inside Word documents
- Multi-user auth, roles, clinic tenancy
- Dedicated job queues / workers (Redis, Celery, RQ, etc.) — in-process `BackgroundTasks` only
- Cloud LLM APIs (paid or remote)
- **Additional site UI languages** beyond English and Spanish (v1 toggle is EN/ES only; document extraction may detect other ISO codes best-effort)
- **Document page preview** (PDF or Word visual viewer; text preview is enough for v1)
- Real-time collaboration / websockets (v1 uses HTTP polling with `processing` percent/messages for user feedback)
- Production hardening (rate limits, audit logs, HIPAA/GDPR compliance program)

## Constraints

- Free and open-source libraries only
- Prefer permissive licenses (MIT/BSD/Apache); avoid AGPL dependencies
- Ollama runs on the host when LLM mode needs it (documented)
- **Failure policy:** if heuristics can produce a usable record, LLM timeout/unavailability MUST NOT force `status=failed` (see `specs/architecture.md` failure matrix)
- Document size/timeout limits via env (`MAX_UPLOAD_BYTES`, `OLLAMA_TIMEOUT_SECONDS`, etc.)
