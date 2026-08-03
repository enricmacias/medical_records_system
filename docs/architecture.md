# Architecture Summary

See also [specs/architecture.md](../specs/architecture.md) and [docs/adr/](./adr/) (including [0001 pdfplumber](./adr/0001-pdf-extraction-pdfplumber.md), [0004 python-docx](./adr/0004-docx-extraction-python-docx.md)).

## Stack

| Concern | Choice |
|---|---|
| Frontend | React + Vite (polls while processing; progressive section loading + progress feedback; **EN/ES site language toggle**) |
| Backend | FastAPI + in-process background tasks |
| Document text | pdfplumber (PDF), python-docx (.docx) |
| Structuring | Heuristics ± Ollama structured outputs (`qwen2.5:7b`); FakeLLM for tests |
| DB | SQLite |
| Files | Local `data/uploads/` |
| Packaging | Docker Compose |

## Key design choices

1. **Spec-anchored SDD** — behavior lives in `specs/` before code.
2. **Adapter interfaces** — document extractors and LLM can be swapped without API changes.
3. **Hybrid extraction** — heuristics first (inline compound demographics, label-free species/breed, global inference, pet name/breed validation, visit blocks); species normalized to Dog/Cat and sex to Male/Female when inferable; optional LLM for weak clinical hints (narrative) and/or summary polish; heuristic clinical summary always generated; timeout falls back to heuristics.
4. **Async by default** — upload returns `processing`; UI polls until `completed`/`failed`; partial pet/owner/meta and `processing` percent/messages appear before clinical summary completes.
5. **Human-in-the-loop** — pet (six demographic fields) and owner are editable; clinical summary and meta are read-only in v1. Site UI in English or Spanish (toggle); document language separate (`meta.source_language`). **Confidence UX** highlights missing and uncertain fields from `meta` without API changes.
6. **Fake LLM** — tests and demos work without GPU/model download.

## Assumptions

- Uploads are text-based PDF or .docx (not scanned PDFs or image-only Word content; legacy .doc not supported)
- Single user, no auth
- Ollama is optional for many multi-visit historiales under `hybrid`/`heuristic` (heuristic clinical summary always produced); polish and narrative LLM require Ollama or use `llm` mode for weak-hint documents
- Ollama, when used from Docker, is typically reached via `host.docker.internal` (Mac/Windows) or documented host networking on Linux
- Multilingual **document extraction** is intentional (Spanish clinic headers and historiales are first-class); other languages best-effort via the LLM when invoked. **Site UI** localization is English/Spanish only (see `specs/data-model.md` UI localization).

## Failure policy

See the failure matrix in [specs/architecture.md](../specs/architecture.md). Health `ollama: unavailable` is informational under hybrid/heuristic modes.

## Future improvements

See [future-improvements.md](./future-improvements.md).
