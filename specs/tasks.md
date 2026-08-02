# Implementation Tasks

Ordered slices. Each task maps to acceptance criteria in `specs/acceptance.md`.

## T0 — Specs (done)

- [x] `problem.md`, `scope.md`, `data-model.md`, `api.md`, `acceptance.md`
- [x] `architecture.md` + ADRs

## T1 — Skeleton

- [x] Backend FastAPI app with `/api/health`
- [x] SQLite wiring + settings
- [x] React Vite shell
- [x] Docker Compose (API + frontend)
- [x] Project README

## T2 — Upload + store

- [x] `POST /api/records` accepts PDF and .docx, stores file, creates DB row
- [x] `GET /api/records`, `GET /api/records/{id}`, `GET /api/records/{id}/file`
- [x] Reject unsupported formats / oversized files (legacy `.doc` rejected with clear error)
- [x] Frontend upload + list

## T3 — Extract text

- [x] pdfplumber adapter (PDF); python-docx adapter added in T17
- [x] Persist `raw_text`
- [x] Frontend extracted-text preview (on-demand toggle; hidden by default)
- [x] Fixture PDF + unit test; .docx fixture + tests in T17

## T4 — Structure with LLM / heuristics

- [x] Domain Pydantic schema matching data-model
- [x] Ollama structurer (`format` + schema)
- [x] FakeLLM structurer
- [x] Wire into upload pipeline; handle failures
- [x] Show structured data in UI (Pet, Owner, Clinical summary, Meta)

## T5 — Edit + persist

- [x] `PATCH /api/records/{id}`
- [x] Structured form read-only by default; Edit / Cancel / Save corrections for presented fields
- [x] Unsaved-changes confirm on Cancel; success notice after save
- [x] Reload persistence check (covered by tests + UI save)

## T6 — Polish

- [x] Full README (install, Ollama, Docker, fake mode)
- [x] `docs/architecture.md` summary + future improvements
- [x] Sample fixture PDF and .docx (T17)
- [x] Acceptance checklist documented

## T7 — Async processing & performance (done)

- [x] `PROCESSING_MODE=async` default with FastAPI `BackgroundTasks`
- [x] UI polling while `status=processing`
- [x] Hybrid clinical mode: heuristics-first; narrative LLM when hints weak; summary polish when hints sufficient (see architecture structuring strategy)
- [x] Skip demographics LLM when `pet.name` hinted
- [x] LLM timeout/error falls back to heuristics instead of hard-failing recoverable cases
- [x] Env knobs: `LLM_CLINICAL_MODE`, `OLLAMA_TIMEOUT_SECONDS`, `OLLAMA_NUM_PREDICT`, `OLLAMA_NUM_CTX`
- [x] Unit tests for hybrid/heuristic modes, fallbacks, async vs sync API

## T8 — Spec alignment (done)

- [x] Update scope/architecture/api/data-model/acceptance/tasks for async + hybrid reality
- [x] Update ADR 0002 and docs summaries; remove async from “future only”

## T9 — Record detail UI + frontend tests (done)

- [x] Collapse extracted text behind **Extracted text**; structured view read-only until **Edit**
- [x] Clinical summary (≤2000 chars, extraction-time prose); slim persisted schema (Pet / Owner / clinical.history / Meta)
- [x] Save next to Cancel; discard warning; save success notice
- [x] Vitest + Testing Library coverage for helpers, RecordForm, RecordPage
- [x] Align specs (scope/architecture/data-model/acceptance/tasks) with this UI

## T10 — Inline compound demographics + tests (done)

- [x] Parse inline compound header lines (`NAME - Nacimiento: DATE`, `Nombre …`, `Hembra Estado: …` for sex)
- [x] Inline `Label: value` segments; standalone `Hembra`/`Macho`; mixed-case names
- [x] Compound-name sanitization when generic `Nombre`/`Name` captures the full line
- [x] Inline hints override/repair earlier `pet.name` guesses
- [x] `tests/test_inline_demographics.py` + updates to Spanish/performance integration tests
- [x] Align specs (data-model extraction notes, scope, architecture, acceptance, tasks)

## T11 — Label-free species/breed + Dog/Cat normalization (done)

- [x] Infer species and breed from header lines without `Especie:` / `Raza:` labels (standalone species, dash compound, space-separated)
- [x] Normalize species to canonical **`Dog`** / **`Cat`** in heuristics, LLM fallbacks, and UI display/save
- [x] Feminine species tokens (`canina`, `felina`, `gata`) hint `Hembra` when sex not already set
- [x] Breed plausibility guards (reject address fragments and demographic noise); labeled fields override unlabeled hints
- [x] `tests/test_unlabeled_species_breed.py`; frontend species normalization tests; align specs (data-model, scope, architecture, acceptance, tasks)

## T12 — Remove pet weight and coat_color (done)

- [x] Drop `pet.weight` and `pet.coat_color` from domain schema, heuristics, LLM structurers, tests, and specs
- [x] `Hembra Estado: … Peso: …` compound lines still set `pet.sex` only

## T13 — Clinical summary (done)

- [x] `adapters/clinical_summary.py`: heuristic prose summary → `clinical.history` (≤2000 chars, Spanish/English, sanitization)
- [x] Optional LLM summary polish pass (`ClinicalSummaryPolish`); gating per `LLM_CLINICAL_MODE` (inverse of narrative LLM in hybrid)
- [x] UI **Clinical summary** section: read-only always; paragraph preservation
- [x] Save preserves loaded `clinical.history`; dirty check excludes summary
- [x] `tests/test_clinical_summary.py`; frontend RecordForm / `recordDisplay` tests
- [x] Align specs (data-model extraction notes, architecture, acceptance, scope, tasks, ADR, README)

## T14 — Slim persisted structured record (done)

- [x] Persist only pet (six fields), owner, `clinical.history`, and meta via `to_persisted_record()`
- [x] Remove Medications section and non-persisted clinical/visit fields from UI and PATCH payload
- [x] Extraction workspace (`ExtractionRecord`) retains visit/meds/diagnosis for summary generation only
- [x] Align specs (data-model, acceptance, architecture, scope, tasks, problem, docs)

## T15 — Progressive processing UX (done)

- [x] `ProcessingProgress` on `RecordResponse` (`percent`, `step`, `message`); DB progress columns; cleared on terminal status
- [x] Staged `process_record`: persist `raw_text` and partial `structured_data` (pet/owner/meta) mid-flight via `update_during_processing`
- [x] Structurer `on_progress` / `on_partial` callbacks (Ollama + FakeLLM)
- [x] UI: sections render as ready; clinical summary progress bar + messages; Edit disabled while processing
- [x] `tests/test_progressive_processing.py`; frontend RecordForm/RecordPage progressive-loading tests
- [x] Align specs (api, data-model, architecture, acceptance, scope, tasks, docs)

## T16 — Site UI localization EN/ES (done)

- [x] Header language toggle (English / Español); `localStorage` preference; default from browser locale
- [x] Localized UI chrome, labels, status (record detail), processing steps (from `processing.step`), species/sex display, confidence and missing-field labels
- [x] Date display: month name + full year in site language (DOB and dates in clinical summary); raw values on save/edit
- [x] Do not translate: pet name, microchip, owner name; clinical summary prose stays in document language
- [x] Language suggestion banner when `meta.source_language` (`en`/`es`) differs from site language
- [x] Frontend i18n (`frontend/src/i18n/`), `formatDate`, `displayValues`; Vitest coverage
- [x] Align specs (data-model, acceptance, architecture, api, scope, tasks, docs, README)

## T17 — Word (.docx) upload support (done)

- [x] `python-docx` adapter for `.docx` text extraction (paragraphs + table rows)
- [x] `CompositeDocumentExtractor` routes PDF vs .docx by stored extension
- [x] `POST /api/records` accepts PDF and .docx; stores `{id}.pdf` or `{id}.docx` with correct `content_type`
- [x] Reject unsupported formats and legacy `.doc` with clear errors
- [x] Download endpoint streams stored `content_type`
- [x] Frontend: broaden file `accept`; localized strings for PDF + Word; “Download original file”
- [x] `tests/test_document_extractor.py`, docx upload in `tests/test_api.py`, shared `tests/sample_documents.py`
- [x] Align specs (scope, problem, data-model, api, acceptance, architecture, tasks, README, ADR 0001/0003/0004 cross-references)
