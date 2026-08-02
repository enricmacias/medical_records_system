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

Supports multilingual clinic PDFs (especially Spanish/English), **two-column headers**, **inline compound header lines** (multiple fields on one line), **label-free species/breed header tokens** (e.g. `CANINA - YORKSHIRE TERRIER` without `Especie:` / `Raza:`), and long multi-visit histories.

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
  "visit": {
    "date": "string | null",
    "clinic_name": "string | null",
    "veterinarian": "string | null"
  },
  "clinical": {
    "chief_complaint": "string | null",
    "history": "string | null /* Clinical summary: readable prose, max 2000 chars, extraction/re-process only in v1 */",
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

**Pet field notes:** `pet.species` is stored as canonical **`Dog`** or **`Cat`** when inferred or normalized; `null` if unknown. `pet.breed` is free text from the source (e.g. `YORKSHIRE TERRIER`). The pet object has **six** demographic fields only (name, species, breed, sex, date of birth, microchip).

### Field semantics

| Field | Meaning |
|---|---|
| `pet.*` | Animal demographics. In two-column headers (`Datos de la Mascota` \| `Datos del Cliente`), pet is left/first name token — not the owner. **`pet.name` MUST be the animal’s name only** — never a compound string such as `ALYA - Nacimiento: 05/07/2018`. Inline heuristics split name vs date of birth on those patterns. Mixed-case names (e.g. `Alya`) are accepted. |
| `pet.species` | Species / Especie. Pipeline and UI normalize canine/feline tokens to canonical **`Dog`** or **`Cat`** (e.g. `Canino`, `CANINA`, `Perro`, `Dog` → `Dog`; `Felino`, `Felina`, `Gato`, `Cat` → `Cat`). May be inferred **without** an `Especie:` label (see extraction notes). `null` when unknown or ambiguous (e.g. both dog and cat keywords in body with no clear label). |
| `pet.breed` | Breed / Raza. Free-text breed name when present. May be inferred from compound header lines (e.g. `CANINA - YORKSHIRE TERRIER`) without a `Raza:` label. Not inferred when the tail looks like an address fragment, date, or other non-breed noise. |
| `pet.microchip` | Microchip / Nº Chip when present. |
| `pet.sex` | Sex / gender. Recognized from `Sexo:` labels; standalone line-start words (`Hembra`, `Macho`, `Male`, `Female`); compound lines such as **`Hembra Estado: FERTIL Peso:0`** (sex only — weight on the line is not stored); and feminine species tokens (`canina`, `felina`, `gata`) on unlabeled species/breed header lines → **`Hembra`** when sex is not already set. |
| `owner.address` | Postal address lines when recoverable from header layout. |
| `visit` | Summary of the **most recent** visit (date, clinic, vet if known) — not the full history. Stored by the pipeline; **not shown** as its own section in the v1 record form. |
| `clinical.chief_complaint` / `examination` / `treatment` | Synthesis biased to **recent** clinically important content. Stored by the pipeline; **not directly edited** in the v1 form. Feed **heuristic clinical summary** generation and the UI display fallback when `clinical.history` is empty. |
| `clinical.history` | **Clinical summary** (stored field name `history`). Readable prose generated at **upload / re-process** only (max **2000** characters). Written as 1–4 short paragraphs (`\n\n` separators) with complete sentences — not bullet fragments. Highlights diagnoses, visit timeline, examination findings, treatment, and **brief** medication mentions (full drug list remains in `clinical.medications`). **Language:** Spanish prose when `meta.source_language` is `es`; English otherwise. **Content rules:** excludes pet/owner demographics; strips weight tokens, chip-like numbers, and duplicate medication names from visit snippets; skips redundant chief complaint when it duplicates the latest visit; filters generic pipeline notes. **Read-only** in the v1 form (not edited on save; PATCH preserves the loaded value). Any `history` text produced by the optional **clinical narrative** LLM is **overwritten** by summary generation at the end of structuring. |
| `clinical.diagnosis` | Main conditions (comma/semicolon-separated if several). Stored; used in heuristic summary generation and as part of the UI display fallback when `history` and `history_entries` are empty. |
| `clinical.medications` | Important drugs across visits (typically up to ~8); dose/frequency when known. UI presents as a single multi-line list (fully editable). Brief drug names may also appear in the clinical summary. |
| `clinical.history_entries` | Dated visit highlights. Cap **12** entries: keep early context + most recent visits when the historial is longer. Summaries may be truncated. Feed heuristic summary generation; used for **legacy UI fallback** (dated lines) when `history` is empty; not edited row-by-row in v1. |
| `meta.source_language` | ISO 639-1 when detectable (`es`, `en`, …). |
| `meta.extraction_confidence` | Pipeline self-assessment (`low` / `medium` / `high`). |
| `meta.missing_fields` | Important paths still empty after extraction (e.g. `pet.name`, `pet.species`, `pet.breed`). Listed when null/empty after structuring; inference failures are not invented — they appear here or remain `null`. |

## UI presentation (record detail)

The full JSON above remains the persistence/API contract. The structured form shows a **subset** for human review:

| Section | Source | Notes |
|---|---|---|
| Pet | six `pet` fields | **Name**, **Species**, **Breed**, **Sex**, **Date of birth**, **Microchip** — read-only until Edit. Species displays and saves as **`Dog`** or **`Cat`** (Spanish/English source tokens normalized on display and PATCH). |
| Owner | `owner.*` | Name, phone, email, address; read-only until Edit. |
| Clinical summary | `clinical.history` | **Clinical summary** (max **2000** characters), **read-only** always (including in Edit mode). Hint: “Auto-generated on upload; not editable.” Display order: (1) non-empty `history` from extraction (paragraph breaks preserved via `pre-wrap`); (2) if `history` empty, dated lines from `history_entries`; (3) if both empty, join `diagnosis`, `chief_complaint`, and `treatment`. Changes to `clinical.history` do **not** mark the form dirty. |
| Medications | `clinical.medications` | One multi-line field: one medication per line; optional `Name (dosage, frequency)`. Parsed back into the medications array on save. |
| Meta | `meta.*` | Confidence, language, missing fields (display only). |

**Not presented** as editable sections in v1: `visit`, `clinical.history_entries` (row editor), `chief_complaint`, `examination`, `diagnosis`, `treatment`, `notes`.

**Edit interaction:** structured sections are read-only by default. **Edit** enables inputs; **Save corrections** PATCHes `structured_data`; **Cancel** exits edit mode and discards unsaved edits (with a confirm dialog when dirty). A success notice is shown after save. Species is edited via a **Dog / Cat** select; read-only display shows normalized labels.

**Save semantics:** the form updates `pet` (six fields), `owner`, and `clinical.medications` from the visible controls. `clinical.history` is **preserved** from the loaded record (clinical summary is not editable and is only regenerated by the pipeline on upload/re-process). Other structured keys present on the record (e.g. `visit`, `history_entries`, unused clinical fields) are **retained** in the PATCH payload unless the client omits them — they are not cleared by the v1 UI.

## Validation rules

- Backend validates `structured_data` with Pydantic on LLM output and on PATCH
- `medications` and `history_entries` default to `[]` when absent
- `meta.extraction_confidence` defaults to `low` if omitted
- `meta.missing_fields` lists human-readable paths that were null/empty after extraction
- `meta.source_language` should be an ISO 639-1 code when detectable
- **Clinical summary length:** generation truncates `clinical.history` to **2000** characters (paragraph/sentence-aware ellipsis). UI displays up to **2000** characters. Pydantic does **not** enforce max length on PATCH — clients should not edit the summary in v1
- On PATCH, client normalizes `pet.species` to **`Dog`** or **`Cat`** when recognizable; otherwise `null`

## Extraction notes

1. **Heuristics first** (`adapters/text_hints.py`): normalize text; detect language; parse Spanish/English labels; chip/clinic/address; split dated visit blocks; diagnosis and medication keyword hints; **inline compound demographic lines** and **label-free species/breed header patterns** (see below). Demographic heuristics scan the **header region (first ~80 lines)** for line-based patterns.
2. **Inline compound demographics** (header region):
   - **`NAME - Nacimiento: DATE`** — e.g. `ALYA - Nacimiento: 05/07/2018` → `pet.name`, `pet.date_of_birth`
   - **`Nombre NAME - Nacimiento: DATE`** — same split after the `Nombre` prefix
   - **English `Name NAME - Nacimiento: DATE`** — same pattern for EN labels
   - **`Hembra Estado: FERTIL Peso:0`** (and `Macho …`) → `pet.sex` only; **`Estado` (e.g. FERTIL) and weight tokens on the line are not stored**
   - **Inline `Label: value` segments** on one line: `Nacimiento:`, `Sexo:`, `Especie:`, `Raza:`, chip labels, etc. (`Peso:` / weight labels are not mapped to pet fields)
   - **Compound-name repair:** if a generic `Nombre`/`Name` rule captures the full line into `pet.name`, sanitize and split before persisting; inline hints override earlier guesses when they disagree.
3. **Label-free species and breed** (header region, same ~80-line window):
   - **Standalone species line** — e.g. `Canino`, `Dog`, `Cat` on its own line → `pet.species` (normalized to `Dog` / `Cat`)
   - **Dash compound** — e.g. `CANINA - YORKSHIRE TERRIER`, `Canino - Labrador Retriever` → `pet.species` + `pet.breed`; feminine species tokens (`canina`, `felina`, `gata`) also hint **`Hembra`** for `pet.sex` when not already set
   - **Space-separated** — e.g. `Felina Persa` → `pet.species` + `pet.breed` (same sex hint rule for feminine tokens)
   - **Supported species tokens** (ES/EN): `canino`, `canina`, `canine`, `perro`, `felino`, `felina`, `feline`, `gato`, `gata`, `dog`, `cat` (case-insensitive)
   - **Body fallback** — `infer_species_from_text()` scans the first ~5000 characters when species is still missing: prefers labeled `Especie`/`Species` when present; otherwise a single species keyword family (dog vs cat). Returns **`null`** when both families appear without a clear label (ambiguous).
   - **Breed plausibility** — do **not** set `pet.breed` when the candidate looks like an address (`C/ …`), contains a date, or matches demographic noise (`nacimiento`, `microchip`, `historial`, `cliente`, `propietario`, etc.). Example: `Canino - C/ ORTEGA Y GASSET` → species only.
   - **Normalization** — `apply_species_normalization()` maps hinted or inferred values to **`Dog`** / **`Cat`** before structuring completes.
4. **Hint merge precedence** (demographics):
   - **Inline compound** hints may **override** earlier wrong `pet.name` guesses.
   - **Label-free** species/breed hints use **`setdefault`** — they fill gaps only and do **not** override values already set by labeled parsers (`Especie …`, `Raza …`, inline `Especie:` / `Raza:` segments, or generic label rules).
5. **Demographics LLM:** if `LLM_SKIP_DEMOGRAPHICS_WHEN_HINTED=true` and `pet.name` is hinted, skip demographics LLM and build from hints; otherwise try a short Ollama demographics call and fall back to hints on error.
   - **Caveat:** skip is keyed only on `pet.name` today. A wrong or compound `pet.name` can still skip the LLM and leave DOB/sex/species/breed empty — compound-line and unlabeled heuristics mitigate this; a smarter skip (require name + key fields) is future work.
6. **Clinical field extraction (`LLM_CLINICAL_MODE`)** — populates `chief_complaint`, `examination`, `treatment`, `diagnosis`, `medications`, `history_entries`, and `notes` via heuristics ± optional **clinical narrative** LLM (`ClinicalNarrative` schema):
   - Build structured clinical fields from visit/diagnosis/med heuristics (`_clinical_from_hints`).
   - `heuristic`: no clinical narrative LLM.
   - `hybrid` (default): call clinical narrative LLM **only when clinical hints are weak** (no visit blocks, diagnosis hints, or medication hints).
   - `llm`: always attempt clinical narrative LLM.
   - On narrative LLM timeout/error: keep heuristic clinical fields; `notes` may state that LLM narrative was skipped.
   - **Note:** narrative output may include a `history` field, but it is **not** the persisted clinical summary — see step 7.
7. **Clinical summary (`adapters/clinical_summary.py`)** — always runs at end of structuring (Ollama and FakeLLM) to set `clinical.history`:
   - **Heuristic prose** (`build_heuristic_clinical_summary`): builds readable paragraphs from structured clinical fields (not pet/owner); truncates to 2000 chars.
   - **Optional LLM polish** (`ClinicalSummaryPolish`): separate structured-output pass that rewrites the heuristic baseline into clearer prose. Gating (inverse of narrative LLM in hybrid):
     - `heuristic`: no polish (heuristic summary only).
     - `hybrid`: polish when clinical hints are **sufficient** (visit blocks and/or diagnosis/med hints).
     - `llm`: always attempt polish (may run **after** narrative LLM — up to two clinical LLM calls in `llm` mode).
   - On polish timeout/error: keep heuristic summary.
   - FakeLLM: heuristic summary only (no polish).
8. When any LLM is called: JSON Schema is **inlined** (no `$ref`); prompts use a short focused window; `num_predict` / `num_ctx` cap cost. LLM species output is normalized to **`Dog`** / **`Cat`** when recognizable.
9. Long documents: header + recent tail may be used when sending text to LLM calls; visit-block heuristics still see the full normalized text for dating/splitting.
10. **Re-processing:** extraction and clinical summary improvements apply on **new uploads** or when processing runs again; existing `structured_data` (including `clinical.history`) is not automatically refreshed until re-process or manual PATCH of other fields. There is no separate re-process API in v1 — re-upload or manual correction only.
