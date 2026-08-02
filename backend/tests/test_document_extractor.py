"""Unit tests for document text extraction adapters."""

from __future__ import annotations

from pathlib import Path

from app.adapters.document_extractor import (
    CompositeDocumentExtractor,
    DocxExtractor,
    resolve_upload_format,
)
from tests.sample_documents import make_sample_docx_bytes, make_sample_pdf_bytes


def test_resolve_upload_format_pdf() -> None:
    ext, mime = resolve_upload_format("report.PDF", "application/pdf")
    assert ext == ".pdf"
    assert mime == "application/pdf"


def test_resolve_upload_format_docx() -> None:
    ext, mime = resolve_upload_format(
        "report.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    assert ext == ".docx"
    assert mime == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_resolve_upload_format_rejects_legacy_doc() -> None:
    try:
        resolve_upload_format("old.doc", "application/msword")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "docx" in str(exc).lower()


def test_resolve_upload_format_rejects_txt() -> None:
    try:
        resolve_upload_format("notes.txt", "text/plain")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "docx" in str(exc).lower() or "pdf" in str(exc).lower()


def test_docx_extractor(tmp_path: Path) -> None:
    path = tmp_path / "buddy.docx"
    path.write_bytes(make_sample_docx_bytes())
    text = DocxExtractor().extract(path)
    assert "Buddy" in text
    assert "Otitis" in text


def test_composite_extractor_routes_by_extension(tmp_path: Path) -> None:
    composite = CompositeDocumentExtractor()
    pdf_path = tmp_path / "buddy.pdf"
    pdf_path.write_bytes(make_sample_pdf_bytes())
    docx_path = tmp_path / "buddy.docx"
    docx_path.write_bytes(make_sample_docx_bytes())

    assert "Buddy" in composite.extract(pdf_path)
    assert "Buddy" in composite.extract(docx_path)
