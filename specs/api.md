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

- Field: `file` (required) — PDF only
- Max size: 10 MB (`MAX_UPLOAD_BYTES`)

**Processing (async by default):** store file → return `status: "processing"` immediately → extract + structure in a background task.

**Client contract (async):**

1. Receive `201` with `id` and `status: "processing"`
2. `raw_text` and `structured_data` are typically `null` until processing finishes
3. Poll `GET /api/records/{id}` about every **1.5–2 seconds** until `status` is `completed` or `failed`
4. UI should show a processing state and refresh automatically

Set `PROCESSING_MODE=sync` to wait for the full pipeline before responding (useful for tests).

**Response 201** — `RecordResponse` (often still `processing` in async mode)

**Errors**

- `400` — not a PDF / empty file
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

### `GET /api/records/{id}/file`

Download/stream the original PDF.

**Response 200** — `application/pdf`  
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

`pet_name` may be null while `processing` or if structured data has no pet name.

### RecordResponse

```json
{
  "id": "uuid",
  "original_filename": "string",
  "content_type": "application/pdf",
  "status": "processing | completed | failed",
  "error_message": "string | null",
  "raw_text": "string | null",
  "structured_data": { /* MedicalRecord | null */ },
  "created_at": "iso-datetime",
  "updated_at": "iso-datetime"
}
```

See `specs/data-model.md` for `MedicalRecord` field semantics.
