"""Backward-compatible re-exports; see document_extractor.py."""

from app.adapters.document_extractor import (
    DocumentTextExtractor,
    PdfplumberExtractor,
)

# Historical name used across the codebase and ADRs.
PdfTextExtractor = DocumentTextExtractor
