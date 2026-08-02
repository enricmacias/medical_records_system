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
   - Skip clinical LLM when clinical heuristics are sufficient (visit blocks and/or diagnosis/med hints).
   - Otherwise call a **small** Ollama structured-output narrative pass (`format` + inlined JSON Schema), with capped `num_predict` / `num_ctx`.
4. Default model remains **`qwen2.5:7b`** (env-configurable).
5. On LLM timeout/error, **keep heuristic results** and complete the record when possible rather than failing recoverable cases.
6. Modes `heuristic` and `llm` remain available for speed vs quality trade-offs.

## Consequences

- Multi-visit Spanish clinic PDFs often complete quickly without a clinical LLM call
- JSON shape remains validated by Pydantic; humans edit in the UI
- Reviewers can use `LLM_PROVIDER=fake` or hybrid without a GPU
- Heuristics are template-biased (stronger on ES/EN clinic headers, including label-free species/breed lines); unusual formats still benefit from LLM mode when hardware allows
- “Ollama unavailable” is not always a hard failure under hybrid/heuristic modes
