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

Supports multilingual clinic PDFs (especially Spanish/English), **two-column headers**, **inline compound header lines** (multiple fields on one line), and long multi-visit histories.

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
| `pet.*` | Animal demographics. In two-column headers (`Datos de la Mascota` \| `Datos del Cliente`), pet is left/first name token — not the owner. **`pet.name` MUST be the animal’s name only** — never a compound string such as `ALYA - Nacimiento: 05/07/2018`. Inline heuristics split name vs date of birth on those patterns. Mixed-case names (e.g. `Alya`) are accepted. |
| `pet.microchip` | Microchip / Nº Chip when present. |
| `pet.weight` | **Most recent** weight found in the document. Unit (`kg`, `g`) included when present in the source; bare numbers are kept when the PDF omits a unit (e.g. `Peso:0` → `0`). |
| `pet.sex` | Sex / gender. Recognized from `Sexo:` labels and standalone line-start words (`Hembra`, `Macho`, `Male`, `Female`). |
| `pet.coat_color` | Coat / Capa / color if present. |
| `owner.address` | Postal address lines when recoverable from header layout. |
| `visit` | Summary of the **most recent** visit (date, clinic, vet if known) — not the full history. Stored by the pipeline; **not shown** as its own section in the v1 record form. |
| `clinical.chief_complaint` / `examination` / `treatment` | Synthesis biased to **recent** clinically important content. Stored by the pipeline; **not directly edited** in the v1 form (may feed the clinical resume fallback). |
| `clinical.history` | Short overall narrative / **resume of clinic visits**. UI editing targets this field (max **1000** characters). |
| `clinical.diagnosis` | Main conditions (comma/semicolon-separated if several). Stored; used as resume fallback when history/entries are empty. |
| `clinical.medications` | Important drugs across visits (typically up to ~8); dose/frequency when known. UI presents as a single multi-line list. |
| `clinical.history_entries` | Dated visit highlights. Cap **12** entries: keep early context + most recent visits when the historial is longer. Summaries may be truncated. Used to **synthesize the clinical resume** in the UI when `history` is empty; not edited row-by-row in v1. |
| `meta.source_language` | ISO 639-1 when detectable (`es`, `en`, …). |
| `meta.extraction_confidence` | Pipeline self-assessment (`low` / `medium` / `high`). |
| `meta.missing_fields` | Important paths still empty after extraction (e.g. `pet.name`). |

## UI presentation (record detail)

The full JSON above remains the persistence/API contract. The structured form shows a **subset** for human review:

| Section | Source | Notes |
|---|---|---|
| Pet | `pet.*` | All pet demographic fields; read-only until Edit. |
| Owner | `owner.*` | Name, phone, email, address; read-only until Edit. |
| Clinical record | primarily `clinical.history` | One **Resume of clinic visits** field, max **1000** characters. Display seed: prefer non-empty `history`; else build dated lines from `history_entries`; else join diagnosis / chief_complaint / treatment. |
| Medications | `clinical.medications` | One multi-line field: one medication per line; optional `Name (dosage, frequency)`. Parsed back into the medications array on save. |
| Meta | `meta.*` | Confidence, language, missing fields (display only). |

**Not presented** as editable sections in v1: `visit`, `clinical.history_entries` (row editor), `chief_complaint`, `examination`, `diagnosis`, `treatment`, `notes`.

**Edit interaction:** structured sections are read-only by default. **Edit** enables inputs; **Save corrections** PATCHes `structured_data`; **Cancel** exits edit mode and discards unsaved edits (with a confirm dialog when dirty). A success notice is shown after save.

**Save semantics:** the form updates `pet`, `owner`, `clinical.history`, and `clinical.medications` from the visible controls. Other structured keys present on the record (e.g. `visit`, `history_entries`, unused clinical fields) are **retained** in the PATCH payload unless the client omits them — they are not cleared by the v1 UI.

## Validation rules

- Backend validates `structured_data` with Pydantic on LLM output and on PATCH
- `medications` and `history_entries` default to `[]` when absent
- `meta.extraction_confidence` defaults to `low` if omitted
- `meta.missing_fields` lists human-readable paths that were null/empty after extraction
- `meta.source_language` should be an ISO 639-1 code when detectable
- UI enforces a **1000-character** cap on the clinical resume (`clinical.history` when edited in the form)

## Extraction notes

1. **Heuristics first** (`adapters/text_hints.py`): normalize text; detect language; parse Spanish/English labels; chip/weight/clinic/address; split dated visit blocks; diagnosis and medication keyword hints; **inline compound demographic lines** (see below).
2. **Inline compound demographics** (header region, first ~80 lines):
   - **`NAME - Nacimiento: DATE`** — e.g. `ALYA - Nacimiento: 05/07/2018` → `pet.name`, `pet.date_of_birth`
   - **`Nombre NAME - Nacimiento: DATE`** — same split after the `Nombre` prefix
   - **English `Name NAME - Nacimiento: DATE`** — same pattern for EN labels
   - **`Hembra Estado: FERTIL Peso:0`** (and `Macho …`) → `pet.sex`, `pet.weight`; **`Estado` (e.g. FERTIL) is not stored** in v1
   - **Inline `Label: value` segments** on one line: `Nacimiento:`, `Peso:`, `Sexo:`, `Especie:`, `Raza:`, chip labels, etc.
   - **Compound-name repair:** if a generic `Nombre`/`Name` rule captures the full line into `pet.name`, sanitize and split before persisting; inline hints override earlier guesses when they disagree.
3. **Demographics LLM:** if `LLM_SKIP_DEMOGRAPHICS_WHEN_HINTED=true` and `pet.name` is hinted, skip demographics LLM and build from hints; otherwise try a short Ollama demographics call and fall back to hints on error.
   - **Caveat:** skip is keyed only on `pet.name` today. A wrong or compound `pet.name` can still skip the LLM and leave DOB/sex/weight empty — compound-line heuristics and sanitization mitigate this; a smarter skip (require name + key fields) is future work.
4. **Clinical (`LLM_CLINICAL_MODE`):**
   - Always build a clinical baseline from heuristics (`history_entries`, diagnoses, meds, chief/history when possible).
   - `heuristic`: stop here (no clinical LLM).
   - `hybrid` (default): call a **small clinical narrative** LLM only when clinical hints are weak.
   - `llm`: always attempt the clinical narrative LLM.
5. When LLM is called: JSON Schema is **inlined** (no `$ref`); prompts use a short focused window; `num_predict` / `num_ctx` cap cost.
6. On LLM timeout/error: **keep heuristic clinical data** and complete when possible; notes may state that LLM narrative was skipped.
7. Long documents: header + recent tail may be used when sending text to the LLM; visit-block heuristics still see the full normalized text for dating/splitting.
8. **Re-processing:** extraction improvements apply on **new uploads** or when processing runs again; existing `structured_data` is not automatically refreshed until the record is re-processed or the user edits via PATCH.
