# Acceptance Criteria — Lean MVP

## Functional

- [x] User can upload a PDF or Word (.docx) medical record from the web UI
- [x] Unsupported formats (e.g. `.txt`, legacy `.doc`) are rejected with a clear error (HTTP 400; message mentions .docx/PDF where applicable)
- [x] Uploading `backend/fixtures/sample_vet_record.docx` yields the same buddy-style structuring as the PDF fixture (pet name, clinical summary with Otitis, etc.)
- [x] In async mode, upload returns quickly with `status=processing` and the UI polls until terminal status
- [x] While `status=processing`, the API may return partial `structured_data` (pet, owner, meta) before the clinical summary is ready; UI renders those sections as soon as data is available
- [x] While the clinical summary is still generating, the UI shows **percent progress** and a user-facing step message (`RecordResponse.processing`); **Edit** is disabled until `completed`
- [x] System extracts text from a text-based PDF or .docx; raw text is available on demand via **Extracted text** (not shown by default)
- [x] System produces structured JSON matching `specs/data-model.md` (slim persisted shape: pet, owner, `clinical.history`, meta)
- [x] Structured **`pet`** and the record-detail **Pet** section expose exactly **six** demographic fields — **`name`**, **`species`**, **`breed`**, **`sex`**, **`date_of_birth`**, **`microchip`**. UI **labels** are localized (EN/ES); canonical English labels: Name, Species, Breed, Sex, Date of birth, Microchip. No other pet fields (e.g. weight, coat color) appear in the persisted schema, UI, or editable form.
- [x] **Site language toggle** (English / Español) in the header; UI chrome and field labels follow site language, **independent** of document `meta.source_language`
- [x] **Pet name**, **pet microchip**, and **owner name** values are **not translated** by site language
- [x] Species **stored** as canonical **`Dog`** / **`Cat`** when normalized; **displayed** localized (Dog/Perro, Cat/Gato). Sex **stored** as canonical **`Male`** / **`Female`** when normalized; **displayed** localized in read-only mode (Male/Macho, Female/Hembra); **Save corrections** normalizes recognizable sex codes to **`Male`** / **`Female`** via species/sex selects in edit mode
- [x] Dates in the structured record (**date of birth** and dates in clinical summary) are **displayed** with **month name** and **full year** in the site language; stored values remain original clinic format or ISO
- [x] When document language (`en`/`es`) differs from site language, a **dismissible banner** offers to switch site language
- [x] **Clinical summary** prose stays in the **document language** (not translated by site toggle); only embedded dates are reformatted for display
- [x] Structured record UI shows **only** Pet, Owner, **Clinical summary**, and Meta — no Medications section, no visit section, no separate diagnosis/treatment fields
- [x] Structured record is **read-only by default**; **Edit** enables Pet and Owner fields only; changes persist via PATCH **Save corrections**
- [x] Canceling edit with unsaved changes prompts before discarding; a successful save shows a success notice
- [x] User can list previous records and open one for review
- [x] Original uploaded file (PDF or .docx) remains downloadable
- [x] Spanish multi-visit historial-style text can yield pet/owner demographics, language `es`, and a readable **Clinical summary** in stored JSON (on LLM failure or `heuristic` mode, visit/diagnosis/medication hints feed the **heuristic fallback** workspace only — not stored as separate fields)
- [x] **Clinical summary** (`clinical.history`): readable prose (≤2000 characters), generated at upload/re-process; read-only in the UI; excludes pet/owner demographics; may briefly mention medications in prose; Spanish when `source_language` is `es`
- [x] **`meta.clinical_summary_source`** records how the summary was produced: `llm` (LLM succeeded), `heuristic_fallback` (LLM attempted but failed/timed out/empty), `heuristic` (no LLM — `heuristic` mode or FakeLLM), or null (no summary generated)
- [x] When `meta.clinical_summary_source` is **`heuristic_fallback`**, the UI shows a localized **fallback notice** above the clinical summary (EN/ES); no notice for `llm`, `heuristic`, or null
- [x] Partial `structured_data` during processing omits `meta.clinical_summary_source` until the clinical summary step completes
- [x] Editing and saving Pet or Owner does **not** change the clinical summary; summary changes require re-upload/re-process
- [x] Inline compound header lines split into separate pet fields — e.g. `ALYA - Nacimiento: 05/07/2018` → name `ALYA` and DOB `05/07/2018`; `Nombre ALYA - Nacimiento: …` and `Hembra Estado: FERTIL Peso:0` → sex `Female` (`pet.name` must not contain `Nacimiento:`; weight on compound lines is not stored)
- [x] When `meta.extraction_confidence` is `low`, the structured form shows a notice and highlights **empty** highlightable fields (all six pet fields, all owner fields, and clinical summary when empty) with **Uncertain** badges; fields in `meta.missing_fields` are always highlighted with **Not extracted** badges (even when confidence is medium/high)
- [x] Field highlights remain in **edit mode**; **Save corrections** does not clear `meta.missing_fields` — badges persist until re-upload/re-process (v1 intentional)
- [x] Label-free species and breed header lines infer pet demographics without `Especie:` / `Raza:` labels — e.g. standalone `Canino` → species `Dog`; `CANINA - YORKSHIRE TERRIER` → species `Dog`, breed `YORKSHIRE TERRIER`, sex hint `Female`; `Felina Persa` → species `Cat`, breed `Persa`. Labeled `Especie` / `Raza` values take precedence over unlabeled lines on the same document. Address-like breed tails (e.g. `Canino - C/ ORTEGA …`) do not populate `pet.breed`. Species stored as canonical **`Dog`** / **`Cat`** when inferred; sex stored as canonical **`Male`** / **`Female`** when inferred; UI may display localized species and sex labels per site language.
- [x] **Global demographic inference** scans the header region (~100 lines) and pipe-table rows (e.g. `Breed: | Domestic Shorthair | Sex | Female`) to fill missing pet/owner fields when line-start matchers fail; also runs **`validate_and_refine_pet_name`** so `pet.name` may be upgraded to a higher-ranked candidate
- [x] **Pet name extraction** collects multiple header candidates, **scores** them by source strength and context (demographic proximity, repeat mentions, owner-token penalties), and picks the **highest-scoring validated** name — e.g. `Pet: LUNA` wins over an earlier clinic-line `MARLEY` caps token; `Nombre MARLEY` wins over standalone `TOBY` near species labels
- [x] **Pet name format heuristics** support mixed-case colon labels (`Name: Luna`), `Nombre`/`Name` prefix lines, quoted names (`Pet: "Buddy"`, `"Max"` on its own line near demographics, `Se llama 'Luna'`), and title-case standalone lines **only** when adjacent to species/breed/sex/chip context (ignored otherwise)
- [x] **`Nombre PET OWNER…`** header lines split into `pet.name` and `owner.name` (mixed-case supported), e.g. `Nombre Luna Beatriz Abarca` → pet `Luna`, owner `Beatriz Abarca`
- [x] **Pet name validation** rejects generic non-name words (e.g. Summary, Grammar, punctuation) during extraction; invalid candidates are dropped; **`validate_and_refine_pet_name`** is final authority in the heuristic pass
- [x] **Breed validation** during extraction accepts only recognized dog/cat breeds from a finite catalog (`adapters/pet_breed_catalog.py`); unknown or non-breed tokens are dropped and the scan continues (first valid catalog match); manual PATCH may still store any breed string the user enters

## Technical

- [x] FastAPI REST API implements `specs/api.md`
- [x] Extraction uses pdfplumber (PDF) and python-docx (.docx) behind a `DocumentTextExtractor` interface
- [x] Structuring uses hybrid heuristics ± Ollama structured outputs (`format` + JSON Schema) per `LLM_CLINICAL_MODE` (optional single **text-first** clinical summary LLM — see `specs/architecture.md`)
- [x] Default model is `qwen2.5:7b` (env-configurable)
- [x] Fake LLM adapter allows tests without a live Ollama instance (including heuristic clinical summary)
- [x] Hybrid/heuristic paths can complete multi-visit records without a live Ollama instance when historial hints exist
- [x] Hybrid/heuristic paths can complete records with inline compound demographics without a live Ollama instance when header hints suffice
- [x] Hybrid/heuristic paths can complete records with label-free species/breed header lines without a live Ollama instance when header hints suffice
- [x] Docker Compose starts API + frontend
- [x] README documents install, Ollama setup, async/hybrid modes, and run steps
- [x] Specs and architecture docs explain decisions and assumptions

## Quality bar

- [x] Backend unit/integration tests cover extraction (**`tests/test_document_extractor.py`**, pdfplumber + python-docx), docx upload in **`tests/test_api.py`**, heuristics/hybrid modes (inline compound demographics in **`tests/test_inline_demographics.py`**, label-free species/breed in **`tests/test_unlabeled_species_breed.py`**, global inference in **`tests/test_global_demographic_inference.py`**, **ranked pet-name inference and format heuristics in `tests/test_pet_name_inference.py`**, demographic validation in **`tests/test_demographic_validation.py`**, breed catalog validation in **`tests/test_pet_breed_validation.py`**, clinical summary in **`tests/test_clinical_summary.py`** and **`tests/test_clinical_summary_pipeline.py`**, hybrid/fallback modes in **`tests/test_performance_modes.py`**, progressive processing in **`tests/test_progressive_processing.py`**), schema validation, async/sync API paths (with FakeLLM)
- [x] Frontend unit tests (Vitest) cover display helpers (including `buildClinicalResume` / clinical summary, species normalization for `CANINA` / `Felina`, **sex normalization** (`M`/`Macho` → `Male`, `H`/`Hembra` → `Female`), **`formatDate` / `displayValues`**, **`fieldConfidence`**, **`LanguageContext` / `LanguageToggle` / `LanguageSuggestionBanner`**), RecordForm view/edit/save (six pet fields including **sex select**, clinical summary read-only and preserved on save, **progress while summary generating**, **fallback notice when `clinical_summary_source=heuristic_fallback`**, **`clinical_summary_source` preserved on save**, **localized labels and date display**, **missing/low-confidence field highlighting**), and RecordPage extracted-text / edit-cancel / save-notice / **partial-data and processing-panel** / **language suggestion** flows
- [x] Failure matrix honored: Ollama down/timeout does not force `failed` when heuristics produce usable structured data; unrecoverable errors set `failed` with `error_message`
- [x] Health reports Ollama reachability without silently inventing empty structured payloads
- [x] Code organized for maintainability (adapters/services/domain separation)

## Demo path

1. Start stack (`docker compose up` or local dev). Ollama optional for hybrid historial demos (heuristic clinical summary still generated on timeout); pull `qwen2.5:7b` when using live Ollama for improved summaries.
2. Upload sample PDF fixture and/or sample .docx fixture and/or a Spanish multi-visit style document.
3. Optionally upload or paste-test a document (PDF or .docx) whose header uses **inline compound lines** (`ALYA - Nacimiento: …`, `Nombre … - Nacimiento: …`, or `Hembra Estado: …`), **`Nombre PET OWNER…`** splits (`Nombre Luna Beatriz Abarca`), **label-free species/breed lines** (`Canino` alone, `CANINA - YORKSHIRE TERRIER`, or `Felina Persa`), **ranked pet-name patterns** (`Pet: LUNA` with clinic noise above; `Name: Luna`; title-case `Luna` between species/breed lines), **quoted names** (`Pet: "Buddy"`), or **docx-style pipe rows** (`Breed: | Domestic Shorthair | Sex | Female`).
4. Observe `processing` on the record page (async). Watch **percent progress** and step messages; confirm **Pet** and **Owner** appear before the **Clinical summary** finishes (progress bar in summary section until text is ready).
5. When `completed`, review the **Structured record** (Pet with six fields, Owner, **Clinical summary**, Meta). Confirm `pet.name` is not a compound string and is not a generic document word (e.g. Summary). Confirm species shows as **Dog** or **Cat** (or **Perro** / **Gato** when site is Spanish). Confirm sex shows localized labels (e.g. **Macho** / **Hembra** in Spanish UI) while stored values are **`Male`** / **`Female`** after save. Confirm breed, when present, is a plausible breed name (not header noise). Confirm date of birth uses **month name and full year** in site language. Confirm clinical summary is readable prose without pet/owner names or weight. Optionally open **Extracted text** (also available mid-processing after text extraction). For a record with `extraction_confidence: low` or non-empty `missing_fields`, confirm **field highlights** (badges + borders), the **low-confidence banner** when applicable, and warning styling on the Meta confidence value. Optionally confirm `meta.clinical_summary_source` in API JSON (`llm` when Ollama succeeds; `heuristic` with FakeLLM or `LLM_CLINICAL_MODE=heuristic`).
6. **Optional fallback demo:** stop Ollama or set a very low `OLLAMA_TIMEOUT_SECONDS`, re-upload a historial document under `hybrid`/`llm`, and confirm **`heuristic_fallback`** in `structured_data.meta` plus the **fallback notice** above the clinical summary in the UI (EN and ES).
7. Toggle **English / Español** in the header — confirm labels and date formatting change; confirm **pet name**, **microchip**, and **owner name** stay the same. For a Spanish document with English site language, confirm the **language suggestion** banner appears.
8. Confirm **Edit** is disabled while processing; after completion, click **Edit**, change a Pet or Owner field, **Save corrections** — confirm the success notice; reload and verify the change persists, **clinical summary is unchanged**, and **`meta.clinical_summary_source` is preserved**. Optionally **Cancel** to exercise the unsaved-changes prompt.
9. Note: records processed **before** a schema change may contain extra keys in `structured_data` until re-uploaded; the API ignores unknown keys on read/PATCH.
