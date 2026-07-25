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

### `POST /api/records`

Multipart form upload.

- Field: `file` (required) — PDF only
- Max size: 10 MB

**Processing (sync):** store file → extract text → structure via LLM → persist → return record.

**Response 201** — `RecordResponse`

**Errors**

- `400` — not a PDF / empty file
- `413` — too large
- `422` — validation
- `500` — unexpected server error

On extraction/LLM failure the endpoint still returns **201** with `status: "failed"` and `error_message` set, so the upload is not lost.

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
