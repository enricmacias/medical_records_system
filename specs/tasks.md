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

- [x] `POST /api/records` accepts PDF, stores file, creates DB row
- [x] `GET /api/records`, `GET /api/records/{id}`, `GET /api/records/{id}/file`
- [x] Reject non-PDF / oversized files
- [x] Frontend upload + list

## T3 — Extract text

- [x] pdfplumber adapter
- [x] Persist `raw_text`
- [x] Frontend extracted-text preview (on-demand toggle; hidden by default)
- [x] Fixture PDF + unit test

## T4 — Structure with LLM / heuristics

- [x] Domain Pydantic schema matching data-model
- [x] Ollama structurer (`format` + schema)
- [x] FakeLLM structurer
- [x] Wire into upload pipeline; handle failures
- [x] Show structured data in UI (Pet, Owner, Clinical record resume, Medications list, Meta)

## T5 — Edit + persist

- [x] `PATCH /api/records/{id}`
- [x] Structured form read-only by default; Edit / Cancel / Save corrections for presented fields
- [x] Unsaved-changes confirm on Cancel; success notice after save
- [x] Reload persistence check (covered by tests + UI save)

## T6 — Polish

- [x] Full README (install, Ollama, Docker, fake mode)
- [x] `docs/architecture.md` summary + future improvements
- [x] Sample fixture PDF
- [x] Acceptance checklist documented

## T7 — Async processing & performance (done)

- [x] `PROCESSING_MODE=async` default with FastAPI `BackgroundTasks`
- [x] UI polling while `status=processing`
- [x] Hybrid clinical mode: heuristics-first; skip clinical LLM when hints sufficient
- [x] Skip demographics LLM when `pet.name` hinted
- [x] LLM timeout/error falls back to heuristics instead of hard-failing recoverable cases
- [x] Env knobs: `LLM_CLINICAL_MODE`, `OLLAMA_TIMEOUT_SECONDS`, `OLLAMA_NUM_PREDICT`, `OLLAMA_NUM_CTX`
- [x] Unit tests for hybrid/heuristic modes, fallbacks, async vs sync API

## T8 — Spec alignment (done)

- [x] Update scope/architecture/api/data-model/acceptance/tasks for async + hybrid reality
- [x] Update ADR 0002 and docs summaries; remove async from “future only”

## T9 — Record detail UI + frontend tests (done)

- [x] Collapse extracted text behind **Extracted text**; structured view read-only until **Edit**
- [x] Clinical record resume (≤1000 chars) + single medications list; keep Pet / Owner / Meta
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
