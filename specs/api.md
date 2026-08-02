# API Contract

Base path: `/api`

All JSON responses use UTF-8. Errors use:

```json
{ "detail": "message or validation errors" }
```

## Endpoints

### `GET /api/health`

Returns service health and LLM reachability.

**Response 200**

```json
{
  "status": "ok",
  "ollama": "available" | "unavailable" | "skipped",
  "model": "qwen2.5:7b"
}
```

Notes:

- `skipped` when `LLM_PROVIDER=fake`
- `unavailable` means Ollama is not reachable; with `LLM_CLINICAL_MODE=hybrid|heuristic` uploads may still complete via heuristics
- Does not by itself block record creation

### `POST /api/records`

Multipart form upload.

- Field: `file` (required) — **PDF** or **Word (.docx)** only. Legacy binary **`.doc` is not supported**.
- Max size: 10 MB (`MAX_UPLOAD_BYTES`)

Accepted MIME types:

| Format | Extension | `content_type` |
|---|---|---|
| PDF | `.pdf` | `application/pdf` |
| Word (modern) | `.docx` | `application/vnd.openxmlformats-officedocument.wordprocessingml.document` |

Validation uses file extension and/or `Content-Type`. Extension matching is **case-insensitive** (`.PDF`, `.DOCX` accepted). When extension and MIME disagree, **extension wins** (e.g. `report.docx` with `application/pdf` is treated as .docx).

Some browsers send `application/octet-stream` for `.docx`; the extension is the reliable fallback. If **both** filename and MIME are ambiguous (e.g. missing filename defaults server-side to `upload.pdf`, empty MIME), validation follows the resolved name/MIME rules above — clients should send a correct filename and extension.

**Example `400` responses** (`detail` string):

| Case | Example `detail` |
|---|---|
| Unsupported type | `Only PDF and Word (.docx) files are supported` |
| Legacy `.doc` | `Legacy Word (.doc) is not supported. Please upload .docx or PDF.` |
| Empty file | `Uploaded file is empty` |

**Processing (async by default):** store file → return `status: "processing"` immediately → extract + structure in a background task.

**Client contract (async):**

1. Receive `201` with `id` and `status: "processing"` (`processing` may be `null` until the first progress write).
2. Poll `GET /api/records/{id}` about every **1.5–2 seconds** until `status` is `completed` or `failed`.
3. While `status=processing`, the API may return **partial data** as each stage finishes:
   - `raw_text` — typically available after document text extraction (~15% progress).
   - `structured_data` — partial **pet**, **owner**, and **meta** before the clinical summary is ready (`clinical.history` null/empty); full record including summary when `completed`.
   - `processing` — percent, step id, and user-facing message for the current stage (see `ProcessingProgress` below); `null` when not yet started or after terminal status.
4. UI should show processing feedback (progress bar / messages), render structured sections as soon as `structured_data` is present, and refresh automatically.

Set `PROCESSING_MODE=sync` to wait for the full pipeline before responding (useful for tests). Sync responses return `completed` or `failed` with full data and `processing: null`.

**Response 201** — `RecordResponse` (often still `processing` in async mode)

**Errors**

- `400` — unsupported format / empty file / legacy `.doc` (see example `detail` strings above)
- `413` — too large
- `422` — validation
- `500` — unexpected server error

On unrecoverable extraction/structuring failure the record is updated to `status: "failed"` with `error_message` set (async) or returned that way (sync). LLM timeout with usable heuristics should yield `completed` (see architecture failure matrix).

### `GET /api/records`

List records (newest first).

**Response 200**

```json
{
  "items": [ /* RecordSummary */ ]
}
```

### `GET /api/records/{id}`

**Response 200** — `RecordResponse`  
**404** — not found

Used as the polling endpoint while `status=processing`.

### `PATCH /api/records/{id}`

Update structured data after human review.

**Body**

```json
{
  "structured_data": { /* MedicalRecord */ }
}
```

**Response 200** — `RecordResponse`  
**404** — not found  
**422** — invalid schema

Clients may send `pet.species` as **`Dog`** or **`Cat`** (v1 UI normalizes Spanish/English tokens on save). The v1 UI edits **pet** (six demographic fields) and **owner** only. See `specs/data-model.md` for the full persisted shape.

`clinical.history` (**clinical summary**) is **system-generated** on upload/re-process. The v1 UI does not edit it; PATCH preserves the loaded value. Backend does not enforce the 2000-character cap on PATCH (generation truncates at extraction time).

**PATCH during processing:** the v1 UI disables **Edit** while `status=processing`. The API does not reject PATCH on a processing record, but clients should avoid human corrections until `completed` to prevent conflicting with in-flight structuring.

### `GET /api/records/{id}/file`

Download/stream the original uploaded file (PDF or .docx).

**Response 200** — `application/pdf` or `application/vnd.openxmlformats-officedocument.wordprocessingml.document` (matches stored `content_type`). Response uses `original_filename` as the download name (`Content-Disposition` / `filename` on `FileResponse`).  
**404** — not found

## Schemas

### RecordSummary

```json
{
  "id": "uuid",
  "original_filename": "string",
  "status": "processing | completed | failed",
  "created_at": "iso-datetime",
  "updated_at": "iso-datetime",
  "pet_name": "string | null"
}
```

`pet_name` may be null while `processing` (before partial demographics are saved) or if structured data has no pet name. Once partial `structured_data` includes `pet.name`, list `pet_name` may update on the next list fetch.

`RecordSummary` does **not** include `content_type`; the v1 list UI infers format from `original_filename` extension only (no file-type badge).

### ProcessingProgress

Surfaced on `RecordResponse.processing` while `status=processing` and progress has been written. Cleared (`null`) on `completed`, `failed`, and after PATCH.

```json
{
  "percent": 0,
  "step": "string",
  "message": "string"
}
```

| Field | Description |
|---|---|
| `percent` | Integer 0–100; approximate completion for user feedback (not a strict time estimate). |
| `step` | Machine step id (e.g. `starting`, `extracting_text`, `demographics`, `clinical_analysis`, `clinical_summary`, `clinical_summary_polish`, `completing`). **v1 web UI localizes progress text from `step` and `percent`**, not from `message`. |
| `message` | Short user-facing description of the current step (English from backend). API clients may display this directly; the v1 React UI maps `step` (+ `percent` ≥ 35 for `demographics`) to localized strings instead. |

Typical stages (see `specs/architecture.md` for pipeline detail):

| Step | ~% | Example message |
|---|---|---|
| `starting` | 5 | Starting to process your document… |
| `extracting_text` | 15 | Reading text from your document… |
| `demographics` | 20–35 | Extracting pet and owner details… / Pet and owner details are ready… |
| `clinical_analysis` | 50 | Reviewing visits, diagnoses, and medications… |
| `clinical_summary` | 65 | Writing the clinical summary… |
| `clinical_summary_polish` | 80 | Polishing the clinical summary with AI… |
| `completing` | 95 | Saving your structured record… |

**Client note (v1 UI):** Spanish equivalents exist for all `step` ids in frontend i18n. When `step` is `demographics` and `percent` ≥ 35, the UI shows the “pet and owner ready” message rather than the “extracting demographics” message.

### RecordResponse

```json
{
  "id": "uuid",
  "original_filename": "string",
  "content_type": "application/pdf | application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "status": "processing | completed | failed",
  "error_message": "string | null",
  "raw_text": "string | null",
  "structured_data": { /* MedicalRecord | null */ },
  "processing": { /* ProcessingProgress | null */ },
  "created_at": "iso-datetime",
  "updated_at": "iso-datetime"
}
```

`processing` is `null` when `status` is `completed` or `failed`, and may be `null` briefly at the start of async processing before the first progress write.

See `specs/data-model.md` for `MedicalRecord` field semantics, partial-state rules during `processing`, and **Confidence UX** (frontend highlighting from `meta.extraction_confidence` and `meta.missing_fields` — no additional API fields).
