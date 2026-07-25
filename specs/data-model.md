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
| `raw_text` | string \| null | Extracted PDF text |
| `structured_data` | JSON \| null | Validated medical record object |
| `created_at` | ISO datetime | Creation time |
| `updated_at` | ISO datetime | Last update time |

## Structured medical record (`structured_data`)

Unknown values MUST be `null` (or empty list). The model MUST NOT invent clinical facts.

```json
{
  "pet": {
    "name": "string | null",
    "species": "string | null",
    "breed": "string | null",
    "sex": "string | null",
    "date_of_birth": "string | null"
  },
  "owner": {
    "name": "string | null",
    "phone": "string | null",
    "email": "string | null"
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
    "notes": "string | null"
  },
  "meta": {
    "source_language": "string | null",
    "extraction_confidence": "low | medium | high",
    "missing_fields": ["string"]
  }
}
```

## Validation rules

- Backend validates `structured_data` with Pydantic on LLM output and on PATCH
- `medications` defaults to `[]` when absent
- `meta.extraction_confidence` defaults to `low` if the model omits it
- `meta.missing_fields` lists human-readable paths that were null/empty after extraction
