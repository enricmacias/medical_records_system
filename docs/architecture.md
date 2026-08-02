# Architecture Summary

See also [specs/architecture.md](../specs/architecture.md) and [docs/adr/](./adr/).

## Stack

| Concern | Choice |
|---|---|
| Frontend | React + Vite (polls while processing) |
| Backend | FastAPI + in-process background tasks |
| PDF text | pdfplumber |
| Structuring | Heuristics ± Ollama structured outputs (`qwen2.5:7b`); FakeLLM for tests |
| DB | SQLite |
| Files | Local `data/uploads/` |
| Packaging | Docker Compose |

## Key design choices

1. **Spec-anchored SDD** — behavior lives in `specs/` before code.
2. **Adapter interfaces** — PDF and LLM can be swapped without API changes.
3. **Hybrid extraction** — heuristics first (inline compound demographics, label-free species/breed, visit blocks); optional LLM for weak clinical hints (narrative) and/or summary polish; heuristic clinical summary always generated; timeout falls back to heuristics; species normalized to Dog/Cat when inferable.
4. **Async by default** — upload returns `processing`; UI polls until `completed`/`failed`.
5. **Human-in-the-loop** — pet (six demographic fields) and owner are editable; clinical summary and meta are read-only in v1.
6. **Fake LLM** — tests and demos work without GPU/model download.

## Assumptions

- PDFs are text-based (not scanned)
- Single user, no auth
- Ollama is optional for many multi-visit historiales under `hybrid`/`heuristic` (heuristic clinical summary always produced); polish and narrative LLM require Ollama or use `llm` mode for weak-hint documents
- Ollama, when used from Docker, is typically reached via `host.docker.internal` (Mac/Windows) or documented host networking on Linux
- Multilingual support is intentional (Spanish clinic headers and historiales are first-class); other languages best-effort via the LLM when invoked

## Failure policy

See the failure matrix in [specs/architecture.md](../specs/architecture.md). Health `ollama: unavailable` is informational under hybrid/heuristic modes.

## Future improvements

See [future-improvements.md](./future-improvements.md).
