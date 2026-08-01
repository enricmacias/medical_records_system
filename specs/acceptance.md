# Acceptance Criteria — Lean MVP

## Functional

- [x] User can upload a PDF medical record from the web UI
- [x] Non-PDF uploads are rejected with a clear error
- [x] In async mode, upload returns quickly with `status=processing` and the UI polls until terminal status
- [x] System extracts text from a text-based PDF and shows a preview when available
- [x] System produces structured JSON matching `specs/data-model.md`
- [x] Structured fields are editable in the UI and persist via PATCH
- [x] User can list previous records and open one for review
- [x] Original PDF remains downloadable
- [x] Spanish multi-visit historial-style text can yield pet/owner demographics, language `es`, visit highlights, and key clinical hints

## Technical

- [x] FastAPI REST API implements `specs/api.md`
- [x] Extraction uses pdfplumber behind an interface
- [x] Structuring uses hybrid heuristics ± Ollama structured outputs (`format` + JSON Schema) per `LLM_CLINICAL_MODE`
- [x] Default model is `qwen2.5:7b` (env-configurable)
- [x] Fake LLM adapter allows tests without a live Ollama instance
- [x] Hybrid/heuristic paths can complete multi-visit records without a live Ollama instance when historial hints exist
- [x] Docker Compose starts API + frontend
- [x] README documents install, Ollama setup, async/hybrid modes, and run steps
- [x] Specs and architecture docs explain decisions and assumptions

## Quality bar

- [x] Backend unit/integration tests cover extraction, heuristics/hybrid modes, schema validation, async/sync API paths (with FakeLLM)
- [x] Failure matrix honored: Ollama down/timeout does not force `failed` when heuristics produce usable structured data; unrecoverable errors set `failed` with `error_message`
- [x] Health reports Ollama reachability without silently inventing empty structured payloads
- [x] Code organized for maintainability (adapters/services/domain separation)

## Demo path

1. Start stack (`docker compose up` or local dev). Ollama optional for hybrid historial demos; for full LLM narrative pull `qwen2.5:7b` and ensure Ollama is running.
2. Upload sample PDF fixture and/or a Spanish multi-visit style document.
3. Observe `processing` then `completed` on the record page (async).
4. Review raw text + structured form (language, demographics, visit highlights when applicable).
5. Edit a field and reload — change persists.
