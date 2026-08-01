# Data Model

## Record (persisted)

| Field | Type | Description |
|---|---|---|
| `id` | UUID string | Primary key |
| `original_filename` | string | Uploaded file name |
| `stored_path` | string | Relative path on disk |
| `content_type` | string | Always `application/pdf` in v1 |
| `status` | enum | `processing` \| `completed` \| `failed` |
| `error_message` | string \| null | Failure detail if `failed` |
| `raw_text` | string \| null | Extracted PDF text (`null` while `processing` in async mode) |
| `structured_data` | JSON \| null | Validated medical record object (`null` while `processing`) |
| `created_at` | ISO datetime | Creation time |
| `updated_at` | ISO datetime | Last update time |

## Structured medical record (`structured_data`)

Unknown values MUST be `null` (or empty list). The pipeline MUST NOT invent clinical facts.

Supports multilingual clinic PDFs (especially Spanish/English), two-column headers, and long multi-visit histories.

```json
{
  "pet": {
    "name": "string | null",
    "species": "string | null",
    "breed": "string | null",
    "sex": "string | null",
    "date_of_birth": "string | null",
    "microchip": "string | null",
    "weight": "string | null",
    "coat_color": "string | null"
  },
  "owner": {
    "name": "string | null",
    "phone": "string | null",
    "email": "string | null",
    "address": "string | null"
  },
  "visit": {
    "date": "string | null",
    "clinic_name": "string | null",
    "veterinarian": "string | null"
  },
  "clinical": {
    "chief_complaint": "string | null",
    "history": "string | null",
    "examination": "string | null",
    "diagnosis": "string | null",
    "treatment": "string | null",
    "medications": [
      {
        "name": "string | null",
        "dosage": "string | null",
        "frequency": "string | null"
      }
    ],
    "history_entries": [
      {
        "date": "string | null",
        "summary": "string | null"
      }
    ],
    "notes": "string | null"
  },
  "meta": {
    "source_language": "string | null",
    "extraction_confidence": "low | medium | high",
    "missing_fields": ["string"]
  }
}
```

### Field semantics

| Field | Meaning |
|---|---|
| `pet.*` | Animal demographics. In two-column headers (`Datos de la Mascota` \| `Datos del Cliente`), pet is left/first name token — not the owner. |
| `pet.microchip` | Microchip / Nº Chip when present. |
| `pet.weight` | **Most recent** weight found in the document (with unit when available). |
| `pet.coat_color` | Coat / Capa / color if present. |
| `owner.address` | Postal address lines when recoverable from header layout. |
| `visit` | Summary of the **most recent** visit (date, clinic, vet if known) — not the full history. |
| `clinical.chief_complaint` / `examination` / `treatment` | Synthesis biased to **recent** clinically important content. |
| `clinical.history` | Short overall narrative of the case (not every visit verbatim). |
| `clinical.diagnosis` | Main conditions (comma/semicolon-separated if several). |
| `clinical.medications` | Important drugs (typically up to ~8); dose/frequency when known. |
| `clinical.history_entries` | Dated visit highlights. Cap **12** entries: keep early context + most recent visits when the historial is longer. Summaries may be truncated. |
| `meta.source_language` | ISO 639-1 when detectable (`es`, `en`, …). |
| `meta.extraction_confidence` | Pipeline self-assessment (`low` / `medium` / `high`). |
| `meta.missing_fields` | Important paths still empty after extraction (e.g. `pet.name`). |

## Validation rules

- Backend validates `structured_data` with Pydantic on LLM output and on PATCH
- `medications` and `history_entries` default to `[]` when absent
- `meta.extraction_confidence` defaults to `low` if omitted
- `meta.missing_fields` lists human-readable paths that were null/empty after extraction
- `meta.source_language` should be an ISO 639-1 code when detectable

## Extraction notes

1. **Heuristics first** (`adapters/text_hints.py`): normalize text; detect language; parse Spanish/English labels; chip/weight/clinic/address; split dated visit blocks; diagnosis and medication keyword hints.
2. **Demographics:** if `LLM_SKIP_DEMOGRAPHICS_WHEN_HINTED=true` and `pet.name` is hinted, skip demographics LLM and build from hints; otherwise try a short Ollama demographics call and fall back to hints on error.
3. **Clinical (`LLM_CLINICAL_MODE`):**
   - Always build a clinical baseline from heuristics (`history_entries`, diagnoses, meds, chief/history when possible).
   - `heuristic`: stop here (no clinical LLM).
   - `hybrid` (default): call a **small clinical narrative** LLM only when clinical hints are weak.
   - `llm`: always attempt the clinical narrative LLM.
4. When LLM is called: JSON Schema is **inlined** (no `$ref`); prompts use a short focused window; `num_predict` / `num_ctx` cap cost.
5. On LLM timeout/error: **keep heuristic clinical data** and complete when possible; notes may state that LLM narrative was skipped.
6. Long documents: header + recent tail may be used when sending text to the LLM; visit-block heuristics still see the full normalized text for dating/splitting.
