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
| `raw_text` | string \| null | Extracted PDF text; `null` until extraction completes; may be set while `status=processing` |
| `structured_data` | JSON \| null | Validated medical record object; `null` until first partial or final write; may be **partial** while `processing` (see below) |
| `processing_progress` | integer \| null | Ephemeral progress percent (0–100); cleared on terminal status |
| `processing_step` | string \| null | Machine step id; cleared on terminal status |
| `processing_message` | string \| null | User-facing step message; cleared on terminal status |
| `created_at` | ISO datetime | Creation time |
| `updated_at` | ISO datetime | Last update time |

Progress columns are persisted only to support polling; they are exposed on the API as `RecordResponse.processing` and cleared when the record reaches `completed` or `failed`.

### Partial `structured_data` while `processing`

During async structuring, the backend may persist and return a **partial** `MedicalRecord` before `status=completed`:

| Present early | Typically empty until completion |
|---|---|
| `pet` (six demographic fields) | — |
| `owner` | — |
| `meta` | — |
| — | `clinical.history` (clinical summary) |

Partial payloads are valid `MedicalRecord` objects. `meta.missing_fields` may include `clinical.history` until the summary is generated. Clients should tolerate `clinical.history` null/empty while `status=processing` and show progress feedback for that section.

## Structured medical record (`structured_data`)

Unknown values MUST be `null` (or empty list). The pipeline MUST NOT invent clinical facts.

**Persisted shape (v1):** only pet demographics (six fields), owner contact, clinical summary, and meta. Visit details, medications lists, diagnosis, visit entry arrays, and other extraction workspace fields are used **during structuring only** and are **not stored** on the record.

Supports multilingual clinic PDFs (especially Spanish/English), **two-column headers**, **inline compound header lines**, **label-free species/breed header tokens**, and long multi-visit histories (for clinical summary generation).

```json
{
  "pet": {
    "name": "string | null",
    "species": "string | null",
    "breed": "string | null",
    "sex": "string | null",
    "date_of_birth": "string | null",
    "microchip": "string | null"
  },
  "owner": {
    "name": "string | null",
    "phone": "string | null",
    "email": "string | null",
    "address": "string | null"
  },
  "clinical": {
    "history": "string | null /* Clinical summary: readable prose, max 2000 chars */"
  },
  "meta": {
    "source_language": "string | null",
    "extraction_confidence": "low | medium | high",
    "missing_fields": ["string"]
  }
}
```

### Pet section — six demographic fields

The `pet` object has **exactly six** fields. These are the only animal demographics persisted, shown in the UI, and editable on save:

| API field | UI label (EN) | UI label (ES) | Notes |
|---|---|---|---|
| `pet.name` | Name | Nombre | Animal name only — never a compound header string. **Value not translated** by site language. |
| `pet.species` | Species | Especie | Stored canonical **`Dog`** or **`Cat`** when normalized; displayed localized (Dog/Perro, Cat/Gato). |
| `pet.breed` | Breed | Raza | Free-text breed when present; value from document, not translated. |
| `pet.sex` | Sex | Sexo | Stored as extracted (e.g. M, H, Macho); **display** localized (Male/Macho, Female/Hembra) in read-only mode. |
| `pet.date_of_birth` | Date of birth | Fecha de nacimiento | **Stored** in original clinic format or ISO; **display** uses long date with month name and full year in site language (see UI localization). |
| `pet.microchip` | Microchip | Microchip | Chip number when present. **Value not translated** by site language. |

No other pet fields (e.g. weight, coat color) exist in the persisted schema, extraction workspace pet model, or UI.

### Field semantics (persisted)

| Field | Meaning |
|---|---|
| `owner.*` | Client/owner name, phone, email, address. |
| `clinical.history` | **Clinical summary** — readable prose generated at upload/re-process (max **2000** characters). Read-only in the UI. Workspace fields (diagnosis, medications, visit blocks, etc.) feed summary generation but are **not persisted**. Medication names may appear briefly inside the summary text. |
| `meta.source_language` | ISO 639-1 when detectable (`es`, `en`, …). **Document language** — independent of site UI language; shown as raw code in Meta. |
| `meta.extraction_confidence` | Pipeline self-assessment (`low` / `medium` / `high`). |
| `meta.missing_fields` | Persisted paths still empty after extraction. May include: `pet.name`, `pet.species`, `pet.breed`, `owner.name`, `clinical.history`. |

## UI presentation (record detail)

The structured form shows **only** these sections. **Section titles and field labels** follow the **site language** (English or Spanish — see UI localization below).

| Section | Source | Notes |
|---|---|---|
| Pet | six `pet` fields | Labels localized; read-only until Edit. |
| Owner | `owner.*` | Labels localized; owner **name value not translated**. Read-only until Edit. |
| Clinical summary | `clinical.history` | Read-only always (max **2000** characters). **Prose stays in document language**; embedded dates reformatted for display. While `status=processing` and summary not ready, show **progress bar + localized step message** (from `processing.step`, not API `message`). |
| Meta | `meta.*` | Confidence and missing-field labels localized; `source_language` shown as ISO code. May appear in partial structured data before clinical summary completes. |

**Progressive loading (async):** Pet, Owner, and Meta sections render as soon as partial `structured_data` is available. **Clinical summary** is the slowest step on a local LLM; show percent and localized processing step until `clinical.history` is populated or `status=completed`.

**Edit interaction:** Pet and Owner fields are read-only by default. **Edit** enables those inputs only and is **disabled** while `status=processing`. **Clinical summary** and **Meta** remain read-only. In **edit mode**, inputs show **raw stored values** (e.g. `M`, `04/10/19`); species select shows localized labels (Perro/Gato) but saves `Dog`/`Cat`. **Save corrections** PATCHes `structured_data`; **Cancel** discards unsaved edits (confirm when dirty).

**Save semantics:** the form sends only `pet` (six fields), `owner`, `clinical.history` (preserved from load), and `meta` (preserved from load). There is no Medications section and no other clinical or visit fields in the UI or PATCH payload.

## UI localization (site language)

v1 supports **English** and **Spanish** for the **site UI** only (header toggle). This is **independent** of `meta.source_language` (PDF/extraction language).

| Aspect | Behavior |
|---|---|
| Toggle | Header **English / Español** on all pages; preference in `localStorage` (`vetrecords-ui-locale`); default from browser locale (`es*` → Spanish, else English). |
| Localized | App chrome, section titles, field **labels**, buttons, record-detail **status**, processing **steps** (via `processing.step` + percent), confidence labels, missing-field path labels, species **display** (Dog/Perro, Cat/Gato), sex **display** (read-only), list timestamps (`toLocaleString`). |
| Not localized (values) | **`pet.name`**, **`pet.microchip`**, **`owner.name`** — always shown as stored/extracted. |
| Not translated (content) | **Clinical summary prose** — remains in document language; only **dates within the summary** are reformatted for display. Breed, phone, email, address **values** stay as extracted. |
| Date display | Read-only: **long form** with **month name** and **full year** in site language (e.g. EN: `October 4, 2019`; ES: `4 de octubre de 2019`). Applies to `pet.date_of_birth` and date patterns in clinical summary. Edit mode shows raw stored date strings. |
| Language hint | When `meta.source_language` is `en` or `es` and differs from site language, a dismissible banner offers to switch site language (per-record dismiss in `localStorage`). No hint for other detected languages. |
| Backend | No API changes; localization is **frontend-only**. |

## Validation rules

- Backend validates `structured_data` with Pydantic on structurer output and on PATCH (`extra` fields from legacy records are ignored)
- `meta.extraction_confidence` defaults to `low` if omitted
- `meta.missing_fields` lists paths among persisted fields that are null/empty after extraction
- Clinical summary: generation truncates to **2000** characters; UI displays up to **2000**
- On PATCH, client normalizes `pet.species` to **`Dog`** or **`Cat`** when recognizable

## Extraction notes

Structuring uses a wider **workspace** (`ExtractionRecord` in `domain/extraction_models.py`) with visit blocks, medications, diagnosis, chief complaint, etc. At the end of structuring, `to_persisted_record()` writes only the slim JSON above.

1. **Heuristics first** (`adapters/text_hints.py`): normalize text; detect language; parse Spanish/English labels; chip/clinic/address; split dated visit blocks; diagnosis and medication keyword hints; **inline compound demographic lines** and **label-free species/breed header patterns** (below). Demographic heuristics scan the **header region (first ~80 lines)**.
2. **Inline compound demographics** (header region):
   - **`NAME - Nacimiento: DATE`** → `pet.name`, `pet.date_of_birth`
   - **`Nombre NAME - Nacimiento: DATE`** — same split after the `Nombre` prefix
   - **`Hembra Estado: FERTIL Peso:0`** (and `Macho …`) → `pet.sex` only; weight tokens on the line are not stored
   - Inline `Label: value` segments: `Nacimiento:`, `Sexo:`, `Especie:`, `Raza:`, chip labels (`Peso:` / weight not mapped to pet fields)
   - Compound-name repair when generic `Nombre`/`Name` captures the full line into `pet.name`
3. **Label-free species and breed** (header region):
   - Standalone species line (`Canino`, `Dog`, `Cat`) → `pet.species` (normalized to `Dog` / `Cat`)
   - Dash compound (`CANINA - YORKSHIRE TERRIER`) → species + breed; feminine tokens may hint `Hembra` for sex
   - Space-separated (`Felina Persa`) → species + breed
   - Labeled `Especie` / `Raza` take precedence over unlabeled lines
   - Breed plausibility: reject address fragments, dates, demographic noise
4. **Demographics LLM:** if `LLM_SKIP_DEMOGRAPHICS_WHEN_HINTED=true` and `pet.name` is hinted, skip demographics LLM and build from hints; otherwise try Ollama demographics and fall back to hints on error.
   - **Caveat:** skip is keyed only on `pet.name` today. A wrong or compound `pet.name` can still skip the LLM — inline compound and unlabeled heuristics mitigate this.
5. **Clinical workspace (`LLM_CLINICAL_MODE`):** populate workspace clinical fields via heuristics ± optional **clinical narrative** LLM (`ClinicalNarrative`). These fields are **not persisted**; they feed clinical summary generation. See `specs/architecture.md` for narrative vs polish gating.
6. **Clinical summary (`adapters/clinical_summary.py`):** always run at end of structuring — heuristic prose into `clinical.history`; optional **summary polish** LLM in `hybrid`/`llm` modes. FakeLLM: heuristic summary only.
7. **Re-processing:** demographics and clinical summary refresh on **new upload** or when processing runs again; no separate re-process API in v1.
