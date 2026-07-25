# Architecture

## Overview

A small modular monolith:

- **Frontend (React + Vite):** upload, list, text preview, editable structured form
- **Backend (FastAPI):** REST API, orchestration, persistence
- **Ollama (host):** local LLM for structured extraction
- **SQLite + filesystem:** metadata/JSON in SQLite; PDFs on disk

```text
React ──HTTP──▶ FastAPI
                  ├── adapters/pdfplumber  → raw text
                  ├── adapters/ollama      → structured JSON
                  ├── adapters/fake_llm    → tests/demo
                  └── services/storage     → SQLite + files
```

## Layers

| Layer | Responsibility |
|---|---|
| `api/` | HTTP routes, request/response models, status codes |
| `domain/` | Pydantic medical-record schema (shared source of truth) |
| `services/` | Use-cases: process upload, update record |
| `adapters/` | External I/O: PDF, LLM, DB |

Dependencies point inward: adapters and API depend on domain/services, not the reverse.

## Processing pipeline

1. Validate upload (PDF, size ≤ 10 MB)
2. Persist file under `data/uploads/{id}.pdf`
3. Insert DB row (`status=processing`)
4. Extract text via `PdfTextExtractor`
5. Structure via `MedicalRecordStructurer` (Ollama or Fake)
6. Update row (`completed` + data, or `failed` + error)

Sync processing keeps the Lean MVP simple. Timeouts are configured on the HTTP client to Ollama.

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./data/app.db` | SQLite path |
| `UPLOAD_DIR` | `./data/uploads` | PDF storage |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama HTTP API |
| `OLLAMA_MODEL` | `qwen2.5:7b` | Model name |
| `LLM_PROVIDER` | `ollama` | `ollama` or `fake` |
| `MAX_UPLOAD_BYTES` | `10485760` | 10 MB |
| `CORS_ORIGINS` | `http://localhost:5173` | Frontend origin |

## Frontend structure

- List page: records + upload control
- Detail page: raw text panel + structured form
- Thin API client calling `/api/*`

## Testing strategy

- Unit: pdfplumber adapter with fixture PDF; Pydantic schema; FakeLLM
- API: TestClient with `LLM_PROVIDER=fake`
- Manual: live Ollama demo path in acceptance checklist

## Future extension points

- Swap extractor for Docling/OCR without changing API
- Swap structurer for another OpenAI-compatible local runtime
- Move pipeline steps 4–6 to a background worker when latency grows
