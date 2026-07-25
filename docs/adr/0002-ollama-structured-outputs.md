# ADR 0002 — Local structuring with Ollama structured outputs

## Status

Accepted

## Context

Veterinary PDFs vary widely. Rule-based parsing will not generalize. We need free, local structuring into a fixed JSON schema without cloud API costs or data leaving the machine.

## Decision

- Run **Ollama** locally
- Default model **`qwen2.5:7b`**
- Use Ollama **structured outputs** (`format` = JSON Schema from Pydantic)
- Abstract behind `MedicalRecordStructurer` with a **Fake** implementation for CI

## Consequences

- Reliable JSON shape via constrained decoding
- Privacy-friendly and zero inference cost
- Reviewers must install Ollama (or use `LLM_PROVIDER=fake`)
- Quality depends on model size and prompt; humans can edit results in the UI
