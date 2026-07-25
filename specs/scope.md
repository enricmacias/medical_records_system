# Scope — Lean MVP

## In scope

- Single-user web app (no authentication)
- PDF upload only (text-based / digitally generated PDFs)
- Text extraction with **pdfplumber**
- Structured extraction with **Ollama** (`qwen2.5:7b`) using structured outputs (`format` + JSON Schema)
- Persist original file, raw text, and structured JSON (SQLite + filesystem)
- React UI: upload, text preview, editable structured record
- REST API (FastAPI)
- Docker Compose for API + frontend
- Specs, architecture docs, install instructions, future-work notes
- Fake/fixture LLM path for tests and demos without Ollama

## Out of scope (v1)

- Word, images, and other non-PDF formats
- OCR for scanned/image-only PDFs
- Multi-user auth, roles, clinic tenancy
- Async job queues / background workers
- Cloud LLM APIs (paid or remote)
- PDF visual page viewer (optional later; text preview is enough)
- Real-time collaboration
- Production hardening (rate limits, audit logs, HIPAA/GDPR compliance program)

## Constraints

- Free and open-source libraries only
- Prefer permissive licenses (MIT/BSD/Apache); avoid AGPL dependencies
- Ollama runs on the host (documented); app must fail clearly if unreachable
- Sync processing with documented size/timeout limits
