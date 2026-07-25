# Acceptance Criteria — Lean MVP

## Functional

- [x] User can upload a PDF medical record from the web UI
- [x] Non-PDF uploads are rejected with a clear error
- [x] System extracts text from a text-based PDF and shows a preview
- [x] System produces structured JSON matching `specs/data-model.md`
- [x] Structured fields are editable in the UI and persist via PATCH
- [x] User can list previous records and open one for review
- [x] Original PDF remains downloadable

## Technical

- [x] FastAPI REST API implements `specs/api.md`
- [x] Extraction uses pdfplumber behind an interface
- [x] Structuring uses Ollama structured outputs (`format` + JSON Schema)
- [x] Default model is `qwen2.5:7b` (env-configurable)
- [x] Fake LLM adapter allows tests without a live Ollama instance
- [x] Docker Compose starts API + frontend
- [x] README documents install, Ollama setup, and run steps
- [x] Specs and architecture docs explain decisions and assumptions

## Quality bar

- [x] Backend unit/integration tests cover extraction, schema validation, and API happy path (with FakeLLM)
- [x] Clear failure when Ollama is down (no silent empty structured data)
- [x] Code organized for maintainability (adapters/services/domain separation)

## Demo path

1. Start Ollama and pull `qwen2.5:7b`
2. Start stack (`docker compose up` or local dev)
3. Upload sample PDF fixture
4. Review raw text + structured form
5. Edit a field and reload — change persists
