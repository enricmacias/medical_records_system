# Architecture

## Overview

A small modular monolith:

- **Frontend (React + Vite):** upload, list, on-demand extracted-text preview, read-only structured record with edit mode, **progressive section loading** and progress feedback while `processing`, **site language toggle (EN/ES)**, **confidence UX** (missing/low-confidence field highlights), poll while `processing`
- **Backend (FastAPI):** REST API, orchestration, persistence, in-process background processing
- **Heuristics + Ollama (host):** hybrid structuring; FakeLLM for tests/demos
- **SQLite + filesystem:** metadata/JSON in SQLite; original files (PDF / .docx) on disk

```text
React ──HTTP──▶ FastAPI
                  ├── adapters/document_extractor   → raw text (pdfplumber + python-docx)
                  ├── adapters/text_hints       → layout/visit/diagnosis + inline compound demographics + label-free species/breed + global inference + name/breed validation
                  ├── adapters/llm (ollama|fake)→ demographics ± clinical narrative LLM; FakeLLM
                  ├── adapters/clinical_summary → heuristic clinical summary + optional LLM polish → clinical.history
                  └── services/storage          → SQLite + files
```

Document extraction decisions: [ADR 0001 (pdfplumber)](../../docs/adr/0001-pdf-extraction-pdfplumber.md), [ADR 0004 (python-docx)](../../docs/adr/0004-docx-extraction-python-docx.md).

## Layers

| Layer | Responsibility |
|---|---|
| `api/` | HTTP routes, request/response models, status codes, schedule background work |
| `domain/` | Pydantic medical-record schema, `ProcessingProgress`, shared source of truth |
| `services/` | Use-cases: create upload, process record, update structured data |
| `adapters/` | External I/O: document extraction, heuristics, LLM, DB |

Dependencies point inward: adapters and API depend on domain/services, not the reverse.

## Processing pipeline

### Async mode (default: `PROCESSING_MODE=async`)

1. Validate upload (PDF or .docx, size ≤ 10 MB; reject legacy `.doc`)
2. Persist file under `data/uploads/{id}.pdf` or `data/uploads/{id}.docx`
3. Insert DB row (`status=processing`)
4. **Return 201 immediately** with the processing record
5. Background task (staged updates via `update_during_processing`):
   - Record progress (`starting` ~5%)
   - Extract text via `DocumentTextExtractor` (composite: pdfplumber for PDF, python-docx for .docx); persist `raw_text` (~15%)
   - Structure via `MedicalRecordStructurer` with optional `on_progress` / `on_partial` callbacks:
     - Demographics → persist partial `structured_data` (pet, owner, meta; `clinical.history` empty) (~35%)
     - Clinical analysis, heuristic summary, optional polish → progress updates (~50–95%)
   - Final update: `completed` + full data (including `clinical.history`), clear progress — or `failed` + `error_message`, clear progress

Structurers emit progress through callbacks; `RecordService` persists each stage so polling clients can render sections incrementally.

### Sync mode (`PROCESSING_MODE=sync`)

Same steps 1–3, then run extraction/structuring before the HTTP response (used by tests).

In-process FastAPI `BackgroundTasks` is intentional for Lean MVP — not a durable queue.

## Structuring strategy (`LLM_CLINICAL_MODE`)

Clinical structuring uses **two optional LLM passes** after heuristics (see `specs/data-model.md` extraction notes §5–6):

1. **Clinical narrative LLM** (`ClinicalNarrative`) — fills workspace fields (`chief_complaint`, `examination`, `treatment`, `notes`; not persisted).
2. **Clinical summary** — always sets persisted `clinical.history` via heuristic prose; optional **summary polish** LLM rewrites that baseline.

| Mode | Clinical narrative LLM | Summary polish LLM | Clinical summary source |
|---|---|---|---|
| `heuristic` | Never | Never | Heuristic prose only (fastest) |
| `hybrid` (default) | When hints **weak** | When hints **sufficient** | Heuristic ± polish |
| `llm` | Always | Always | Heuristic ± polish (up to **two** clinical LLM calls) |

**Heuristic sufficiency (clinical):** at least one dated visit block, or diagnosis hints, or medication hints.

**Demographics LLM:** skipped when a **validated** `pet.name` is present in hints (`validated_pet_name`; see data-model extraction note §4). Caveat: skip is keyed on validated name only — junk tokens do not skip the LLM. **Pet name in hints** is set by ranked heuristics + `validate_and_refine_pet_name` at the end of the layout-hint pass (see data-model extraction note §1).

**On LLM timeout/error:** keep heuristic clinical fields and heuristic summary; complete the record when possible; do not fail solely because Ollama timed out.

## Failure matrix

| Situation | Expected `status` |
|---|---|
| Invalid/unsupported/oversized upload | HTTP 400/413; no record (or not created) |
| Document stored; text extract + structure succeed | `completed` |
| Multi-visit document (PDF or .docx); Ollama down; heuristics sufficient (`hybrid`/`heuristic`) | `completed` (heuristic-filled structured data + heuristic clinical summary) |
| Valid upload format but text extraction fails (corrupt PDF/.docx, password-protected .docx) | `failed` + `error_message` (extractor error) |
| Clinical narrative LLM attempted and times out; workspace already has clinical hints | `completed` (heuristic clinical summary still set) |
| Summary polish LLM attempted and times out; heuristic summary exists | `completed` (heuristic summary retained) |
| Structurer raises with no recoverable structured data | `failed` + `error_message` |
| FakeLLM provider | `completed` in tests/demos without Ollama |

Health `ollama: unavailable` is **informational** — it does not by itself block hybrid/heuristic completion.

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/app.db` | SQLite path |
| `UPLOAD_DIR` | `./data/uploads` | Original file storage |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` (local); Docker often `http://host.docker.internal:11434` | Ollama HTTP API |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Model name |
| `LLM_PROVIDER` | `ollama` | `ollama` or `fake` |
| `PROCESSING_MODE` | `async` | `async` or `sync` |
| `LLM_CLINICAL_MODE` | `hybrid` | `heuristic` \| `hybrid` \| `llm` |
| `LLM_SKIP_DEMOGRAPHICS_WHEN_HINTED` | `true` | Skip demographics LLM when **validated** `pet.name` found in heuristics (see data-model extraction note §4) |
| `OLLAMA_TIMEOUT_SECONDS` | `90` | HTTP timeout for Ollama calls |
| `OLLAMA_NUM_PREDICT` | `384` | Max generated tokens when LLM is called |
| `OLLAMA_NUM_CTX` | `4096` | Context window for Ollama options |
| `MAX_UPLOAD_BYTES` | `10485760` | 10 MB |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Frontend origins |

**Backend Python dependencies (extraction):** `pdfplumber` (PDF), `python-docx` (.docx) — see `backend/requirements.txt`.

## Frontend structure

- **Site language:** header toggle (English / Español); `localStorage` persistence; independent of `meta.source_language`. See `specs/data-model.md` UI localization.
- List page: records + upload control (upload returns quickly in async mode); list timestamps localized; record `status` on list still shown as API enum (not localized in v1). List shows `original_filename` only — no separate file-type badge; format is inferred from filename extension.
- Upload control: `accept="application/pdf,.pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,.docx"`; localized hint that Word support is **.docx only** (not legacy `.doc`).
- Detail page:
  - Optional **language suggestion** banner when document language (`en`/`es`) differs from site language
  - **Extracted text** toggle (hidden by default) shows `raw_text` when opened (available mid-processing once extraction completes)
  - While `status=processing` and no structured data yet: **Processing your document** panel with percent bar and **localized** step text (from `processing.step`)
  - While `status=processing` with partial structured data: notice that pet/owner are ready; clinical summary still in progress
  - **Structured record** shown as sections become available (Pet, Owner, Meta before clinical summary); read-only by default; labels and display values per site language; **missing/low-confidence field highlighting** per `specs/data-model.md` Confidence UX (badges, borders, low-confidence banner, Meta confidence warning when `low`)
  - **Clinical summary** section: progress bar + localized message while processing and summary empty; summary text when ready (prose not translated; dates reformatted)
  - Status line shows localized `percent · step message` during processing
  - **Edit** enables Pet and Owner only (disabled while `status=processing`); **Save corrections** persists via PATCH; **Cancel** exits edit mode (warns if there are unsaved changes)
  - Success notice after a successful save
  - **Poll `GET /api/records/{id}` ~every 1.5–2s while `status=processing`**
- Thin API client calling `/api/*`
- **i18n:** `frontend/src/i18n/` (translations, `LanguageContext`); display helpers in `frontend/src/lib/formatDate.js`, `displayValues.js`, and `fieldConfidence.js`

## Testing strategy

- Backend unit: document extractors (pdfplumber + python-docx); heuristics (inline compound demographics in `tests/test_inline_demographics.py`; label-free species/breed in `tests/test_unlabeled_species_breed.py`; global inference in `tests/test_global_demographic_inference.py`; demographic validation in `tests/test_demographic_validation.py`; breed catalog in `tests/test_pet_breed_validation.py`); clinical summary in `tests/test_clinical_summary.py`; hybrid/heuristic Ollama paths without network; Pydantic schema; FakeLLM
- Backend unit/service: async returns `processing`; sync completes; `process_record` failure path; progressive processing in `tests/test_progressive_processing.py` (partial persistence, `processing` on GET, callback wiring)
- Backend API: TestClient with `LLM_PROVIDER=fake` and both `PROCESSING_MODE=sync` and `async`
- Frontend unit (Vitest + Testing Library): clinical summary display (`buildClinicalResume`, 2000-char cap, paragraph preservation); species normalization (`Dog`/`Cat`, including `CANINA`/`Felina`); **sex normalization** (`normalizeSexForStorage`, `displayValues`, sex select in RecordForm); **UI i18n** (`LanguageContext`, `LanguageToggle`, `LanguageSuggestionBanner`, `formatDate`, `displayValues`); **`fieldConfidence`** highlight rules; RecordForm (six pet fields, Owner, summary read-only, preserved on save, **clinical summary progress while processing**, **localized labels and date display**, **missing/low-confidence field highlighting** including edit-mode persistence); RecordPage extracted-text toggle, edit/cancel discard dialog, save success notice, **partial structured data and processing panel while processing**, **language suggestion**
- Manual: live Ollama demo path in acceptance checklist (optional when hybrid heuristics suffice); include at least one PDF or .docx with inline compound header lines and/or label-free species/breed header lines; optionally verify polished clinical summary when Ollama is available

## Future extension points

- Swap extractor for Docling/OCR without changing API
- Swap structurer for another OpenAI-compatible local runtime
- Replace in-process background tasks with a durable job queue when needed
- Push transport (SSE/WebSocket) for progress events instead of HTTP polling alone (poll + `processing` field already provides percent/messages in v1)
- Additional **site UI languages** beyond English and Spanish (v1 toggle is EN/ES only; extraction may detect other ISO codes)
- Stronger evaluation set for extraction quality across clinic templates
