"""PDF text extraction adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

import pdfplumber


class PdfTextExtractor(ABC):
    @abstractmethod
    def extract(self, path: Path) -> str:
        raise NotImplementedError


class PdfplumberExtractor(PdfTextExtractor):
    def extract(self, path: Path) -> str:
        chunks: list[str] = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                if text.strip():
                    chunks.append(text)
        return "\n\n".join(chunks).strip()
