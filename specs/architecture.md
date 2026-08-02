# Architecture

## Overview

A small modular monolith:

- **Frontend (React + Vite):** upload, list, on-demand extracted-text preview, read-only structured record with edit mode, poll while `processing`
- **Backend (FastAPI):** REST API, orchestration, persistence, in-process background processing
- **Heuristics + Ollama (host):** hybrid structuring; FakeLLM for tests/demos
- **SQLite + filesystem:** metadata/JSON in SQLite; PDFs on disk

```text
React ──HTTP──▶ FastAPI
                  ├── adapters/pdfplumber       → raw text
                  ├── adapters/text_hints       → layout/visit/diagnosis + inline compound demographics + label-free species/breed
                  ├── adapters/llm (ollama|fake)→ demographics ± clinical narrative LLM; FakeLLM
                  ├── adapters/clinical_summary → heuristic clinical summary + optional LLM polish → clinical.history
                  └── services/storage          → SQLite + files
```

## Layers

| Layer | Responsibility |
|---|---|
| `api/` | HTTP routes, request/response models, status codes, schedule background work |
| `domain/` | Pydantic medical-record schema (shared source of truth) |
| `services/` | Use-cases: create upload, process record, update structured data |
| `adapters/` | External I/O: PDF, heuristics, LLM, DB |

Dependencies point inward: adapters and API depend on domain/services, not the reverse.

## Processing pipeline

### Async mode (default: `PROCESSING_MODE=async`)

1. Validate upload (PDF, size ≤ 10 MB)
2. Persist file under `data/uploads/{id}.pdf`
3. Insert DB row (`status=processing`)
4. **Return 201 immediately** with the processing record
5. Background task:
   - Extract text via `PdfTextExtractor`
   - Structure via `MedicalRecordStructurer` (heuristics ± Ollama / Fake)
   - Update row (`completed` + data, or `failed` + error)

### Sync mode (`PROCESSING_MODE=sync`)

Same steps 1–3, then run extraction/structuring before the HTTP response (used by tests).

In-process FastAPI `BackgroundTasks` is intentional for Lean MVP — not a durable queue.

## Structuring strategy (`LLM_CLINICAL_MODE`)

Clinical structuring uses **two optional LLM passes** after heuristics (see `specs/data-model.md` extraction notes §6–7):

1. **Clinical narrative LLM** (`ClinicalNarrative`) — fills `chief_complaint`, `examination`, `treatment`, `notes` (and transient `history` overwritten later).
2. **Clinical summary** — always sets `clinical.history` via heuristic prose; optional **summary polish** LLM rewrites that baseline.

| Mode | Clinical narrative LLM | Summary polish LLM | Clinical summary source |
|---|---|---|---|
| `heuristic` | Never | Never | Heuristic prose only (fastest) |
| `hybrid` (default) | When hints **weak** | When hints **sufficient** | Heuristic ± polish |
| `llm` | Always | Always | Heuristic ± polish (up to **two** clinical LLM calls) |

**Heuristic sufficiency (clinical):** at least one dated visit block, or diagnosis hints, or medication hints.

**Demographics LLM:** skipped when `pet.name` is hinted (`LLM_SKIP_DEMOGRAPHICS_WHEN_HINTED`); see data-model caveat.

**On LLM timeout/error:** keep heuristic clinical fields and heuristic summary; complete the record when possible; do not fail solely because Ollama timed out.

## Failure matrix

| Situation | Expected `status` |
|---|---|
| Invalid/non-PDF/oversized upload | HTTP 400/413; no record (or not created) |
| PDF stored; text extract + structure succeed | `completed` |
| Multi-visit PDF; Ollama down; heuristics sufficient (`hybrid`/`heuristic`) | `completed` (heuristic-filled structured data + heuristic clinical summary) |
| Clinical narrative LLM attempted and times out; heuristics already filled clinical | `completed` (notes may mention narrative skipped; heuristic summary still set) |
| Summary polish LLM attempted and times out; heuristic summary exists | `completed` (heuristic summary retained) |
| Structurer raises with no recoverable structured data | `failed` + `error_message` |
| FakeLLM provider | `completed` in tests/demos without Ollama |

Health `ollama: unavailable` is **informational** — it does not by itself block hybrid/heuristic completion.

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/app.db` | SQLite path |
| `UPLOAD_DIR` | `./data/uploads` | PDF storage |
| `OLLAMA_BASE_URL` | `http://127.0.0.1:11434` (local); Docker often `http://host.docker.internal:11434` | Ollama HTTP API |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Model name |
| `LLM_PROVIDER` | `ollama` | `ollama` or `fake` |
| `PROCESSING_MODE` | `async` | `async` or `sync` |
| `LLM_CLINICAL_MODE` | `hybrid` | `heuristic` \| `hybrid` \| `llm` |
| `LLM_SKIP_DEMOGRAPHICS_WHEN_HINTED` | `true` | Skip demographics LLM when `pet.name` found in heuristics (fragile if name is wrong/compound — see data-model extraction notes) |
| `OLLAMA_TIMEOUT_SECONDS` | `90` | HTTP timeout for Ollama calls |
| `OLLAMA_NUM_PREDICT` | `384` | Max generated tokens when LLM is called |
| `OLLAMA_NUM_CTX` | `4096` | Context window for Ollama options |
| `MAX_UPLOAD_BYTES` | `10485760` | 10 MB |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Frontend origins |

## Frontend structure

- List page: records + upload control (upload returns quickly in async mode)
- Detail page:
  - **Extracted text** toggle (hidden by default) shows `raw_text` when opened
  - **Structured record** shown read-only by default (Pet — six fields with Dog/Cat species; Owner; **Clinical summary**; Medications list; Meta — see `specs/data-model.md` UI presentation)
  - **Edit** enables fields; **Save corrections** persists via PATCH; **Cancel** exits edit mode (warns if there are unsaved changes)
  - Success notice after a successful save
  - **Poll `GET /api/records/{id}` ~every 1.5–2s while `status=processing`**
- Thin API client calling `/api/*`

## Testing strategy

- Backend unit: pdfplumber adapter; heuristics (inline compound demographics in `tests/test_inline_demographics.py`; label-free species/breed in `tests/test_unlabeled_species_breed.py`); clinical summary in `tests/test_clinical_summary.py`; hybrid/heuristic Ollama paths without network; Pydantic schema; FakeLLM
- Backend unit/service: async returns `processing`; sync completes; `process_record` failure path
- Backend API: TestClient with `LLM_PROVIDER=fake` and both `PROCESSING_MODE=sync` and `async`
- Frontend unit (Vitest + Testing Library): clinical summary display helpers (`buildClinicalResume`, 2000-char cap, paragraph preservation); species normalization (`Dog`/`Cat`, including `CANINA`/`Felina`); RecordForm read-only clinical summary + edit/save payload (six pet fields, summary preserved on save); RecordPage extracted-text toggle, edit/cancel discard dialog, save success notice
- Manual: live Ollama demo path in acceptance checklist (optional when hybrid heuristics suffice); include at least one PDF with inline compound header lines and/or label-free species/breed header lines; optionally verify polished clinical summary when Ollama is available

## Future extension points

- Swap extractor for Docling/OCR without changing API
- Swap structurer for another OpenAI-compatible local runtime
- Replace in-process background tasks with a durable job queue when needed
- Stronger evaluation set for extraction quality across clinic templates
