# ADR 0004 — Word (.docx) extraction with python-docx

## Status

Accepted

## Context

Some clinics export medical records as Word documents. The MVP already extracts PDF text via pdfplumber and feeds plain `raw_text` into the same heuristics + LLM pipeline. We need .docx support without a second structuring path.

Legacy binary Word (`.doc`) requires different libraries (e.g. antiword, LibreOffice) and is uncommon in modern exports.

## Decision

- Accept **`.docx` only** (Office Open XML), not `.doc`.
- Use **python-docx** (MIT) behind the shared `DocumentTextExtractor` interface.
- `CompositeDocumentExtractor` routes by stored file extension: pdfplumber for `.pdf`, python-docx for `.docx`.
- Extract paragraphs and table cell text, joined with blank lines (and ` | ` within table rows) so downstream `text_hints` and LLM see line-oriented plain text similar to PDF extraction.

## Consequences

- Same structuring pipeline for PDF and Word once `raw_text` is available.
- Complex Word layout (text boxes, embedded objects, headers/footers) may be missed — acceptable for v1 clinic exports that are mostly paragraphs and simple tables.
- Users with `.doc` files must convert to `.docx` or PDF before upload (documented in scope and UI hint).
