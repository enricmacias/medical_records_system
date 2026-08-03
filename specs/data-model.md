# Data Model

## Record (persisted)

| Field | Type | Description |
|---|---|---|
| `id` | UUID string | Primary key |
| `original_filename` | string | Uploaded file name |
| `stored_path` | string | Relative path on disk; stored as `{id}.pdf` or `{id}.docx` matching upload format |
| `content_type` | string | `application/pdf` or `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |
| `status` | enum | `processing` \| `completed` \| `failed` |
| `error_message` | string \| null | Failure detail if `failed` |
| `raw_text` | string \| null | Extracted document text; `null` until extraction completes; may be set while `status=processing` |
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

Partial payloads are valid `MedicalRecord` objects. `meta.missing_fields` may include `clinical.history` until the summary is generated. Clients should tolerate `clinical.history` null/empty while `status=processing` and show progress feedback for that section (not missing-field highlights on clinical summary during processing). Pet/owner fields may show **Not extracted** badges from partial `missing_fields` while still `processing`.

## Structured medical record (`structured_data`)

Unknown values MUST be `null` (or empty list). The pipeline MUST NOT invent clinical facts.

**Persisted shape (v1):** only pet demographics (six fields), owner contact, clinical summary, and meta. Visit details, medications lists, diagnosis, visit entry arrays, and other extraction workspace fields are used **during structuring only** and are **not stored** on the record.

Supports multilingual clinic documents (especially Spanish/English), **two-column headers**, **inline compound header lines**, **label-free species/breed header tokens**, and long multi-visit histories (for clinical summary generation).

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
| `pet.name` | Name | Nombre | Animal name only — never a compound header string or generic document word. **Validated on extraction** (proper-name filter); invalid candidates dropped. **Value not translated** by site language. Manual PATCH accepts any non-empty string. |
| `pet.species` | Species | Especie | Stored canonical **`Dog`** or **`Cat`** when normalized; displayed localized (Dog/Perro, Cat/Gato). |
| `pet.breed` | Breed | Raza | On **extraction**, only recognized dog/cat breeds from `adapters/pet_breed_catalog.py` are kept; unknown tokens are omitted (field left empty). On **manual PATCH**, free-text — not catalog-validated. Value not translated. |
| `pet.sex` | Sex | Sexo | Stored canonical **`Male`** / **`Female`** when normalized; **display** localized (Male/Macho, Female/Hembra). Edit mode uses a select; save normalizes recognizable codes. |
| `pet.date_of_birth` | Date of birth | Fecha de nacimiento | **Stored** in original clinic format or ISO; **display** uses long date with month name and full year in site language (see UI localization). |
| `pet.microchip` | Microchip | Microchip | Chip number when present. **Value not translated** by site language. |

No other pet fields (e.g. weight, coat color) exist in the persisted schema, extraction workspace pet model, or UI.

### Field semantics (persisted)

| Field | Meaning |
|---|---|
| `owner.*` | Client/owner name, phone, email, address. |
| `clinical.history` | **Clinical summary** — readable prose generated at upload/re-process (max **2000** characters). Read-only in the UI. Workspace fields (diagnosis, medications, visit blocks, etc.) feed summary generation but are **not persisted**. Medication names may appear briefly inside the summary text. |
| `meta.source_language` | ISO 639-1 when detectable (`es`, `en`, …). **Document language** — independent of site UI language; shown as raw code in Meta. |
| `meta.extraction_confidence` | Pipeline self-assessment (`low` / `medium` / `high`). Drives form-level low-confidence notice and “Uncertain” field badges (see Confidence UX). |
| `meta.missing_fields` | Persisted dot-paths still empty **after extraction completes** (see below). Drives “Not extracted” field badges. Unknown paths (e.g. `raw_text` in tests) are ignored by the UI. |

## UI presentation (record detail)

The structured form shows **only** these sections. **Section titles and field labels** follow the **site language** (English or Spanish — see UI localization below).

| Section | Source | Notes |
|---|---|---|
| Pet | six `pet` fields | Labels localized; read-only until Edit. Fields in `meta.missing_fields` or empty when `extraction_confidence` is `low` are **visually highlighted** (badge + border). |
| Owner | `owner.*` | Labels localized; owner **name value not translated**. Same missing/low-confidence highlighting as Pet. Read-only until Edit. |
| Clinical summary | `clinical.history` | Read-only always (max **2000** characters). **Prose stays in document language**; embedded dates reformatted for display. While `status=processing` and summary not ready, show **progress bar + localized step message** (from `processing.step`, not API `message`) — **no missing/low-confidence highlight** on this section during processing. After completion: highlight when path is in `missing_fields` or when confidence is `low` and summary is still empty. |
| Meta | `meta.*` | Confidence and missing-field path labels localized; `source_language` shown as ISO code. **Summary list** of missing paths (`form.missing`) shown alongside per-field badges (intentional redundancy in v1). Confidence value uses warning styling when `low`. May appear in partial structured data before clinical summary completes. |

**Progressive loading (async):** Pet, Owner, and Meta sections render as soon as partial `structured_data` is available. **Clinical summary** is the slowest step on a local LLM; show percent and localized processing step until `clinical.history` is populated or `status=completed`.

**Confidence UX:** visual feedback so veterinarians can spot weak extraction without reading Meta alone. **No API changes** — driven entirely by `structured_data.meta` on the client.

| Trigger | Badge (EN) | Badge (ES) | Visual |
|---|---|---|---|
| Path in `meta.missing_fields` | Not extracted | No extraído | Solid amber border + tinted background (`field-flagged-missing`); clinical fieldset uses `fieldset-flagged-missing` when `clinical.history` is missing |
| `extraction_confidence` is `low` and field value is empty, path **not** in `missing_fields` | Uncertain | Incierto | Dashed amber border + lighter tint (`field-flagged-low-confidence`) |

**Highlightable field paths** (pet six fields, all `owner.*`, `clinical.history`): `pet.name`, `pet.species`, `pet.breed`, `pet.sex`, `pet.date_of_birth`, `pet.microchip`, `owner.name`, `owner.phone`, `owner.email`, `owner.address`, `clinical.history`.

**`missing_fields` persisted paths** (computed at finalize via `missing_fields_for_persisted()` / `PERSISTED_MISSING_PATHS`): `pet.name`, `pet.species`, `pet.breed`, `owner.name`, `clinical.history` only. Other empty fields (e.g. `owner.phone`, `pet.microchip`) never appear in `missing_fields` but may show **Uncertain** when overall confidence is `low`.

**Priority:** if a path is in `missing_fields`, show **Not extracted** even when confidence is `low` (not both badges).

**When confidence is `medium` or `high`:** only paths in `missing_fields` are highlighted; other empty fields have no highlight.

**Form-level notice** when `extraction_confidence` is `low` (EN: “Extraction confidence is low — review highlighted fields below and fill in any gaps.”; ES: “La confianza de extracción es baja — revisa los campos resaltados y completa los que falten.”).

**While `status=processing`:** pet/owner fields may already show **Not extracted** from partial `missing_fields`; `clinical.history` uses progress UI instead of highlights until processing ends or summary text exists.

**Edit mode:** highlights remain on flagged inputs (`aria-invalid`); filling a field in the UI does **not** remove badges until re-upload/re-process — **Save corrections** preserves loaded `meta` (including `missing_fields`) unchanged in v1.

**Empty display:** highlighted fields still show `—` (`form.empty`) when value is null/empty.

**Default confidence:** if `extraction_confidence` is omitted, backend defaults to `low` — UI may highlight all empty highlightable fields aggressively until meta is populated.

**Pipeline note:** structurers may set interim `missing_fields` during workspace extraction (e.g. only `pet.name`, `pet.species`, `owner.name` in the LLM adapter). **Final** `missing_fields` on `completed` records comes from `to_persisted_record()` / `missing_fields_for_persisted()`, not the interim list.

**i18n keys (frontend):** `form.lowConfidenceNotice`, `form.flagMissing`, `form.flagLowConfidence`, `form.confidenceLabel`, `form.languageLabel`, `form.missing` (Meta summary list); legacy `form.confidence` / `form.language` templates retained but v1 UI uses split label + value for confidence/language rows.

**Edit interaction:** Pet and Owner fields are read-only by default. **Edit** enables those inputs only and is **disabled** while `status=processing`. **Clinical summary** and **Meta** remain read-only. In **edit mode**, species and sex selects show localized labels (Perro/Gato, Macho/Hembra) but save canonical `Dog`/`Cat` and `Male`/`Female`; other pet fields show raw stored values (e.g. `04/10/19`). **Save corrections** PATCHes `structured_data`; **Cancel** discards unsaved edits (confirm when dirty).

**Save semantics:** the form sends only `pet` (six fields), `owner`, `clinical.history` (preserved from load), and `meta` (preserved from load). There is no Medications section and no other clinical or visit fields in the UI or PATCH payload.

## UI localization (site language)

v1 supports **English** and **Spanish** for the **site UI** only (header toggle). This is **independent** of `meta.source_language` (document/extraction language).

| Aspect | Behavior |
|---|---|
| Toggle | Header **English / Español** on all pages; preference in `localStorage` (`vetrecords-ui-locale`); default from browser locale (`es*` → Spanish, else English). |
| Localized | App chrome, section titles, field **labels**, buttons, record-detail **status**, processing **steps** (via `processing.step` + percent; backend `processing.message` is English-generic and is **not** shown by the v1 UI), confidence row labels (`form.confidenceLabel`, `form.languageLabel`), translated confidence **values** (`confidence.low` / `medium` / `high`), missing-field path labels in Meta list (`fields.*`), **confidence UX badges** (`form.flagMissing`, `form.flagLowConfidence`), **low-confidence banner** (`form.lowConfidenceNotice`), species **display** (Dog/Perro, Cat/Gato), sex **display** (read-only), list timestamps (`toLocaleString`). |
| Not localized (values) | **`pet.name`**, **`pet.microchip`**, **`owner.name`** — always shown as stored/extracted. |
| Not translated (content) | **Clinical summary prose** — remains in document language; only **dates within the summary** are reformatted for display. Breed, phone, email, address **values** stay as extracted. |
| Date display | Read-only: **long form** with **month name** and **full year** in site language (e.g. EN: `October 4, 2019`; ES: `4 de octubre de 2019`). Applies to `pet.date_of_birth` and date patterns in clinical summary. Edit mode shows raw stored date strings. |
| Language hint | When `meta.source_language` is `en` or `es` and differs from site language, a dismissible banner offers to switch site language (per-record dismiss in `localStorage`). No hint for other detected languages. |
| Backend | No API changes; localization is **frontend-only**. |

## Validation rules

- Backend validates `structured_data` with Pydantic on structurer output and on PATCH (`extra` fields from legacy records are ignored)
- `meta.extraction_confidence` defaults to `low` if omitted
- `meta.missing_fields` lists paths among **persisted** fields that are null/empty after extraction (final list from `PERSISTED_MISSING_PATHS`; see Confidence UX)
- Clinical summary: generation truncates to **2000** characters; UI displays up to **2000**
- On PATCH, client normalizes `pet.species` to **`Dog`** or **`Cat`** and `pet.sex` to **`Male`** or **`Female`** when recognizable (`normalizeSpeciesForStorage` / `normalizeSexForStorage`); `pet.breed` is trimmed but **not** catalog-validated on save
- **Extraction-only validation** (backend heuristics + structurer fallbacks): `validated_pet_name()` rejects non-proper names; `validated_breed()` requires a match in `pet_breed_catalog`; `resolve_pet_name()` / `resolve_breed()` drop invalid LLM output and prefer valid hints; failed validation leaves the field **empty** (not the rejected token)

## Extraction notes

Structuring uses a wider **workspace** (`ExtractionRecord` in `domain/extraction_models.py`) with visit blocks, medications, diagnosis, chief complaint, etc. At the end of structuring, `to_persisted_record()` writes only the slim JSON above.

1. **Heuristics first** (`adapters/text_hints.py`): normalize text; detect language; parse Spanish/English labels; chip/clinic/address; split dated visit blocks; diagnosis and medication keyword hints; **inline compound demographic lines** and **label-free species/breed header patterns** (below). Demographic heuristics scan the **header region (first ~100 lines)**. **Global inference fallbacks** (`infer_*_from_text`) fill any still-missing pet/owner demographic fields by scanning the header sample for labeled and pipe-table patterns (same strategy as `infer_species_from_text`). **Pet name inference** also treats the word after `patient` / `pet` / `paciente` / `mascota` (with or without `:`) as the name when plausible, scans the header for standalone **ALL-CAPS** tokens/lines (rejecting clinic labels, species, breeds, and other header noise), and **rejects generic non-name words** (e.g. Summary, Grammar, punctuation) — invalid candidates are dropped and the scan continues for a proper pet name.
2. **Inline compound demographics** (header region):
   - **`NAME - Nacimiento: DATE`** → `pet.name`, `pet.date_of_birth`
   - **`Nombre NAME - Nacimiento: DATE`** — same split after the `Nombre` prefix
   - **`Hembra Estado: FERTIL Peso:0`** (and `Macho …`) → `pet.sex` only; weight tokens on the line are not stored
   - Inline `Label: value` segments: `Nacimiento:`, `Sexo:`, `Especie:`, `Raza:`, chip labels (`Peso:` / weight not mapped to pet fields)
   - Compound-name repair when generic `Nombre`/`Name` captures the full line into `pet.name`
3. **Label-free species and breed** (header region):
   - Standalone species line (`Canino`, `Dog`, `Cat`) → `pet.species` (normalized to `Dog` / `Cat`)
   - Dash compound (`CANINA - YORKSHIRE TERRIER`) → species + breed; feminine tokens may hint `Female` for sex
   - Space-separated (`Felina Persa`) → species + breed
   - Labeled `Especie` / `Raza` take precedence over unlabeled lines
   - Breed plausibility: reject address fragments, dates, demographic noise; **known breed validation** via `pet_breed_catalog` rejects non-catalog values (e.g. Summary, Grammar) and continues scanning for a recognized dog/cat breed (English and Spanish names; prefix match e.g. `Labrador` → `Labrador Retriever`)
4. **Demographics LLM:** if `LLM_SKIP_DEMOGRAPHICS_WHEN_HINTED=true` and a **validated** `pet.name` is present in hints (`validated_pet_name`), skip demographics LLM and build from hints; otherwise try Ollama demographics and fall back to hints on error.
   - **Caveat:** skip is keyed on **validated** `pet.name` only. Junk tokens (e.g. Summary) do **not** count as hinted. Compound or wrong names that pass validation can still skip the LLM — inline compound, unlabeled, and global inference mitigate this.
5. **Clinical workspace (`LLM_CLINICAL_MODE`):** populate workspace clinical fields via heuristics ± optional **clinical narrative** LLM (`ClinicalNarrative`). These fields are **not persisted**; they feed clinical summary generation. See `specs/architecture.md` for narrative vs polish gating.
6. **Clinical summary (`adapters/clinical_summary.py`):** always run at end of structuring — heuristic prose into `clinical.history`; optional **summary polish** LLM in `hybrid`/`llm` modes. FakeLLM: heuristic summary only.
7. **Re-processing:** demographics and clinical summary refresh on **new upload** or when processing runs again; no separate re-process API in v1.

### Document text extraction (PDF and .docx)

Both formats produce a single `raw_text` string fed into the same heuristics + LLM pipeline (`DocumentTextExtractor` composite; see `docs/adr/0001-pdf-extraction-pdfplumber.md` and `docs/adr/0004-docx-extraction-python-docx.md`).

| Format | Library | What is extracted |
|---|---|---|
| PDF (`.pdf`) | pdfplumber | Per-page text; blank pages skipped; pages joined with `\n\n` |
| Word (`.docx`) | python-docx | Body **paragraphs** (non-empty); **table** rows as one line per row with cell text joined by ` \| ` |

**Word limitations (v1):** headers/footers, text boxes, footnotes, embedded objects, and image-only content are **not** extracted. Image-only or scanned content inside a .docx is out of scope (same as scanned PDFs — no OCR). Password-protected or corrupt .docx files may fail extraction → `status=failed` with `error_message`.

**Heuristic assumptions:** layout heuristics (header region ~100 lines, inline compound lines, label-free species/breed) operate on **line-oriented plain text**. PDF two-column layout may be merged by pdfplumber; Word loses column structure when flattened to paragraphs — **global inference** re-parses pipe-separated table rows (e.g. `Breed: | Domestic Shorthair | Sex | Female`) into separate fields. Multi-visit historiales in either format use the same visit-block heuristics once `raw_text` is available.

**Empty extraction:** if `raw_text` is empty after extraction (blank PDF, empty .docx, or scanned PDF), structuring may yield low confidence and sparse structured data; unrecoverable extractor errors set `status=failed`.
