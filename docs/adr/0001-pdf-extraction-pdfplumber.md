# ADR 0001 — PDF extraction with pdfplumber

## Status

Accepted (supplemented by ADR 0004 for Word .docx)

## Context

We need reliable text extraction from digitally generated veterinary PDFs for a Lean MVP, using free/open-source libraries with permissive licensing. Word (.docx) support was added later via a separate adapter behind the same `DocumentTextExtractor` interface (see ADR 0004).

## Decision

Use **pdfplumber** (MIT) for PDF files, behind the shared **`DocumentTextExtractor`** interface (`PdfplumberExtractor`). Routing for PDF vs .docx is handled by `CompositeDocumentExtractor` (extension-based).

The historical alias `PdfTextExtractor` remains in `pdf_extractor.py` for backward compatibility.

## Consequences

- Good enough text and table-ish layouts for MVP PDFs
- Permissive license suitable for take-home / commercial follow-up
- No OCR — scanned PDFs will yield empty/poor text (documented limitation)
- Can replace with Docling later without changing the API contract
- PDF and .docx share one `raw_text` → heuristics → LLM pipeline after extraction
