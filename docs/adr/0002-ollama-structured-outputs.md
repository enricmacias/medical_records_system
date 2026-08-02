# ADR 0002 — Hybrid local structuring (heuristics ± Ollama)

## Status

Accepted (amended)

## Context

Veterinary PDFs vary widely across clinics, languages, and templates. Pure rule-based parsing will not generalize to every layout, but calling a local 7B LLM on full multi-visit historiales is slow and often times out behind gateways.

We need free, local structuring into a fixed JSON schema, without cloud API costs or data leaving the machine, while remaining usable on modest hardware.

## Decision

1. Abstract structuring behind `MedicalRecordStructurer` with **Ollama** and **Fake** implementations.
2. Run **layout/visit heuristics first** (Spanish/English headers, chip, inline compound demographics, label-free species/breed header patterns, dated visit blocks, diagnosis/medication hints).
3. Default **`LLM_CLINICAL_MODE=hybrid`**:
   - Skip demographics LLM when `pet.name` is already hinted.
   - **Clinical narrative LLM** (`ClinicalNarrative`): call only when clinical heuristics are **weak** (no visit blocks, diagnosis hints, or medication hints).
   - **Clinical summary polish LLM** (`ClinicalSummaryPolish`): call when clinical heuristics are **sufficient** — rewrites heuristic baseline into readable `clinical.history` prose.
   - Otherwise (weak hints): narrative LLM may run; polish is skipped in hybrid.
4. Always generate **heuristic clinical summary** (`adapters/clinical_summary.py`) at end of structuring; optional polish overwrites when successful.
5. Default model remains **`qwen2.5:7b`** (env-configurable).
6. On LLM timeout/error, **keep heuristic results** (including heuristic summary) and complete the record when possible rather than failing recoverable cases.
7. Modes `heuristic` (no clinical LLM; heuristic summary only) and `llm` (narrative + polish always; up to two clinical LLM calls) remain available for speed vs quality trade-offs.

## Consequences

- Multi-visit Spanish clinic PDFs often complete with heuristic clinical summary without narrative LLM; hybrid may still call Ollama for summary polish when hints are strong
- JSON shape remains validated by Pydantic; humans edit **pet** (six fields) and **owner** in the UI; clinical summary is read-only in v1
- Reviewers can use `LLM_PROVIDER=fake` or hybrid without a GPU (FakeLLM produces heuristic summary)
- Heuristics are template-biased (stronger on ES/EN clinic headers, including label-free species/breed lines); unusual formats still benefit from `llm` mode when hardware allows
- “Ollama unavailable” is not always a hard failure under hybrid/heuristic modes
