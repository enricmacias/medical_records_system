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
- [x] Species **stored** as canonical **`Dog`** / **`Cat`** when normalized; **displayed** localized (Dog/Perro, Cat/Gato). Sex **display** localized in read-only mode (e.g. Male/Macho); raw values preserved on save
- [x] Dates in the structured record (**date of birth** and dates in clinical summary) are **displayed** with **month name** and **full year** in the site language; stored values remain original clinic format or ISO
- [x] When document language (`en`/`es`) differs from site language, a **dismissible banner** offers to switch site language
- [x] **Clinical summary** prose stays in the **document language** (not translated by site toggle); only embedded dates are reformatted for display
- [x] Structured record UI shows **only** Pet, Owner, **Clinical summary**, and Meta — no Medications section, no visit section, no separate diagnosis/treatment fields
- [x] Structured record is **read-only by default**; **Edit** enables Pet and Owner fields only; changes persist via PATCH **Save corrections**
- [x] Canceling edit with unsaved changes prompts before discarding; a successful save shows a success notice
- [x] User can list previous records and open one for review
- [x] Original uploaded file (PDF or .docx) remains downloadable
- [x] Spanish multi-visit historial-style text can yield pet/owner demographics, language `es`, and a readable **Clinical summary** in stored JSON (visit blocks and medications used at extraction time only; not stored as separate fields)
- [x] **Clinical summary** (`clinical.history`): readable prose (≤2000 characters), generated at upload/re-process; read-only in the UI; excludes pet/owner demographics; may briefly mention medications in prose; Spanish when `source_language` is `es`
- [x] Editing and saving Pet or Owner does **not** change the clinical summary; summary changes require re-upload/re-process
- [x] Inline compound header lines split into separate pet fields — e.g. `ALYA - Nacimiento: 05/07/2018` → name `ALYA` and DOB `05/07/2018`; `Nombre ALYA - Nacimiento: …` and `Hembra Estado: FERTIL Peso:0` → sex `Hembra` (`pet.name` must not contain `Nacimiento:`; weight on compound lines is not stored)
- [x] Label-free species and breed header lines infer pet demographics without `Especie:` / `Raza:` labels — e.g. standalone `Canino` → species `Dog`; `CANINA - YORKSHIRE TERRIER` → species `Dog`, breed `YORKSHIRE TERRIER`, sex hint `Hembra`; `Felina Persa` → species `Cat`, breed `Persa`. Labeled `Especie` / `Raza` values take precedence over unlabeled lines on the same document. Address-like breed tails (e.g. `Canino - C/ ORTEGA …`) do not populate `pet.breed`. Species stored as canonical **`Dog`** / **`Cat`** when inferred; UI may display localized species labels (Perro/Gato) per site language.

## Technical

- [x] FastAPI REST API implements `specs/api.md`
- [x] Extraction uses pdfplumber (PDF) and python-docx (.docx) behind a `DocumentTextExtractor` interface
- [x] Structuring uses hybrid heuristics ± Ollama structured outputs (`format` + JSON Schema) per `LLM_CLINICAL_MODE` (clinical narrative + optional clinical summary polish — see `specs/architecture.md`)
- [x] Default model is `qwen2.5:7b` (env-configurable)
- [x] Fake LLM adapter allows tests without a live Ollama instance (including heuristic clinical summary)
- [x] Hybrid/heuristic paths can complete multi-visit records without a live Ollama instance when historial hints exist
- [x] Hybrid/heuristic paths can complete records with inline compound demographics without a live Ollama instance when header hints suffice
- [x] Hybrid/heuristic paths can complete records with label-free species/breed header lines without a live Ollama instance when header hints suffice
- [x] Docker Compose starts API + frontend
- [x] README documents install, Ollama setup, async/hybrid modes, and run steps
- [x] Specs and architecture docs explain decisions and assumptions

## Quality bar

- [x] Backend unit/integration tests cover extraction (**`tests/test_document_extractor.py`**, pdfplumber + python-docx), docx upload in **`tests/test_api.py`**, heuristics/hybrid modes (including inline compound demographics in `tests/test_inline_demographics.py`, label-free species/breed in `tests/test_unlabeled_species_breed.py`, clinical summary in `tests/test_clinical_summary.py`, and progressive processing in `tests/test_progressive_processing.py`), schema validation, async/sync API paths (with FakeLLM)
- [x] Frontend unit tests (Vitest) cover display helpers (including `buildClinicalResume` / clinical summary, species normalization for `CANINA` / `Felina`, **`formatDate` / `displayValues`**, **`LanguageContext` / `LanguageToggle` / `LanguageSuggestionBanner`**), RecordForm view/edit/save (six pet fields, clinical summary read-only and preserved on save, **progress while summary generating**, **localized labels and date display**), and RecordPage extracted-text / edit-cancel / save-notice / **partial-data and processing-panel** / **language suggestion** flows
- [x] Failure matrix honored: Ollama down/timeout does not force `failed` when heuristics produce usable structured data; unrecoverable errors set `failed` with `error_message`
- [x] Health reports Ollama reachability without silently inventing empty structured payloads
- [x] Code organized for maintainability (adapters/services/domain separation)

## Demo path

1. Start stack (`docker compose up` or local dev). Ollama optional for hybrid historial demos (heuristic clinical summary still generated); required for clinical narrative on weak-hint documents and for summary polish on strong-hint documents under `hybrid`. Pull `qwen2.5:7b` when using live Ollama.
2. Upload sample PDF fixture and/or sample .docx fixture and/or a Spanish multi-visit style document.
3. Optionally upload or paste-test a document (PDF or .docx) whose header uses **inline compound lines** (`ALYA - Nacimiento: …`, `Nombre … - Nacimiento: …`, or `Hembra Estado: …`) or **label-free species/breed lines** (`Canino` alone, `CANINA - YORKSHIRE TERRIER`, or `Felina Persa`).
4. Observe `processing` on the record page (async). Watch **percent progress** and step messages; confirm **Pet** and **Owner** appear before the **Clinical summary** finishes (progress bar in summary section until text is ready).
5. When `completed`, review the **Structured record** (Pet with six fields, Owner, **Clinical summary**, Meta). Confirm `pet.name` is not a compound string; confirm species shows as **Dog** or **Cat** (or **Perro** / **Gato** when site is Spanish). Confirm date of birth uses **month name and full year** in site language. Confirm clinical summary is readable prose without pet/owner names or weight. Optionally open **Extracted text** (also available mid-processing after text extraction).
6. Toggle **English / Español** in the header — confirm labels and date formatting change; confirm **pet name**, **microchip**, and **owner name** stay the same. For a Spanish document with English site language, confirm the **language suggestion** banner appears.
7. Confirm **Edit** is disabled while processing; after completion, click **Edit**, change a Pet or Owner field, **Save corrections** — confirm the success notice; reload and verify the change persists and **clinical summary is unchanged**. Optionally **Cancel** to exercise the unsaved-changes prompt.
8. Note: records processed **before** a schema change may contain extra keys in `structured_data` until re-uploaded; the API ignores unknown keys on read/PATCH.
