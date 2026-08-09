# ADR 0002 — Hybrid local structuring (heuristics ± Ollama)

## Status

Accepted (amended)

## Context

Veterinary medical records arrive as **PDF or Word (.docx)** and vary widely across clinics, languages, and templates. Pure rule-based parsing will not generalize to every layout, but calling a local 7B LLM on full multi-visit historiales is slow and often times out behind gateways.

We need free, local structuring into a fixed JSON schema, without cloud API costs or data leaving the machine, while remaining usable on modest hardware.

## Decision

1. Abstract structuring behind `MedicalRecordStructurer` with **Ollama** and **Fake** implementations.
2. Run **layout/visit heuristics first** (Spanish/English headers, chip, inline compound demographics, label-free species/breed header patterns, **global demographic inference** (~100 header lines, pipe-table rows), **ranked pet-name heuristics** with `validate_and_refine_pet_name` at end of hint pass, **pet name proper-name validation**, **breed catalog validation**, species/sex normalization, dated visit blocks, diagnosis/medication hints).
3. Default **`LLM_CLINICAL_MODE=hybrid`**:
   - Skip demographics LLM when a **validated** `pet.name` is already present in hints (`validated_pet_name`).
   - **Clinical summary LLM** (`ClinicalSummaryOutput`): single pass that writes persisted `clinical.history` from **extracted source text** (`clinical_focus_text` — prefers `Historial…` section; ~12k char truncation) plus optional language hint only. **No structured hints or workspace facts** in the LLM prompt.
   - On LLM timeout/error/empty response, build heuristic workspace from hints and fall back to **`build_heuristic_clinical_summary`**, setting `meta.clinical_summary_source = heuristic_fallback`.
4. Modes `heuristic` (no clinical LLM; heuristic summary only) and `llm` (always attempt clinical summary LLM) remain available for speed vs quality trade-offs.
5. Default model remains **`qwen2.5:7b`** (env-configurable). Clinical summary LLM uses a higher `num_predict` (1024) than demographics (384).
6. On LLM timeout/error, **keep heuristic results** (including heuristic summary) and complete the record when possible rather than failing recoverable cases.

## Consequences

- Multi-visit Spanish clinic documents (PDF or .docx) often complete with heuristic clinical summary when Ollama is down or times out. Under `hybrid`/`llm`, Ollama may improve summary quality when available. Structuring consumes plain `raw_text` regardless of source format.
- JSON shape remains validated by Pydantic; humans edit **pet** (six fields) and **owner** in the UI; clinical summary is read-only in v1
- Reviewers can use `LLM_PROVIDER=fake` or hybrid without a GPU (FakeLLM produces heuristic summary)
- Heuristics are template-biased (stronger on ES/EN clinic headers, including label-free species/breed lines, global inference, **ranked pet-name extraction**, and extraction-time name/breed validation); unusual formats still benefit from `llm` mode when hardware allows
- “Ollama unavailable” is not always a hard failure under hybrid/heuristic modes
