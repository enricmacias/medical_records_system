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
- [x] Frontend text preview
- [x] Fixture PDF + unit test

## T4 — Structure with LLM / heuristics

- [x] Domain Pydantic schema matching data-model
- [x] Ollama structurer (`format` + schema)
- [x] FakeLLM structurer
- [x] Wire into upload pipeline; handle failures
- [x] Show structured data in UI

## T5 — Edit + persist

- [x] `PATCH /api/records/{id}`
- [x] Editable form bound to structured fields
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
