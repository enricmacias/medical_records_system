# Architecture Summary

See also [specs/architecture.md](../specs/architecture.md) and [docs/adr/](./adr/).

## Stack

| Concern | Choice |
|---|---|
| Frontend | React + Vite |
| Backend | FastAPI |
| PDF text | pdfplumber |
| Structuring | Ollama structured outputs + `qwen2.5:7b` |
| DB | SQLite |
| Files | Local `data/uploads/` |
| Packaging | Docker Compose |

## Key design choices

1. **Spec-anchored SDD** — behavior lives in `specs/` before code.
2. **Adapter interfaces** — PDF and LLM can be swapped without API changes.
3. **Human-in-the-loop** — LLM output is editable; vets correct mistakes.
4. **Fake LLM** — tests and demos work without GPU/model download.

## Assumptions

- PDFs are text-based (not scanned)
- Single user, no auth
- Ollama is reachable from the API container via `host.docker.internal` (Mac/Windows) or host network notes on Linux
- English-first prompts; other languages best-effort

## Future improvements

See [future-improvements.md](./future-improvements.md).
