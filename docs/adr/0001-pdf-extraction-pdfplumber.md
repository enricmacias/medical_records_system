# ADR 0001 — PDF extraction with pdfplumber

## Status

Accepted

## Context

We need reliable text extraction from digitally generated veterinary PDFs for a Lean MVP, using free/open-source libraries with permissive licensing.

## Decision

Use **pdfplumber** (MIT) behind a `PdfTextExtractor` interface.

## Consequences

- Good enough text and table-ish layouts for MVP
- Permissive license suitable for take-home / commercial follow-up
- No OCR — scanned PDFs will yield empty/poor text (documented limitation)
- Can replace with Docling later without changing the API contract
