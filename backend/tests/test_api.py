"""Backend tests using FakeLLM."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tests.sample_documents import make_sample_docx_bytes, make_sample_pdf_bytes


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db_path = tmp_path / "test.db"
    upload_dir = tmp_path / "uploads"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("UPLOAD_DIR", str(upload_dir))
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.setenv("PROCESSING_MODE", "sync")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:5173")

    from app import config, dependencies

    config.get_settings.cache_clear()
    dependencies.get_store.cache_clear()
    dependencies.get_extractor.cache_clear()
    dependencies.get_structurer.cache_clear()

    from app.main import create_app

    app = create_app()
    with TestClient(app) as test_client:
        yield test_client

    config.get_settings.cache_clear()
    dependencies.get_store.cache_clear()
    dependencies.get_extractor.cache_clear()
    dependencies.get_structurer.cache_clear()


def test_health(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["ollama"] == "skipped"


def test_upload_and_structure(client: TestClient) -> None:
    pdf_bytes = make_sample_pdf_bytes()
    response = client.post(
        "/api/records",
        files={"file": ("buddy.pdf", pdf_bytes, "application/pdf")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body.get("processing") is None
    assert body["raw_text"]
    assert "Buddy" in (body["raw_text"] or "")
    assert body["structured_data"]["pet"]["name"] == "Buddy"
    assert body["structured_data"]["clinical"]["history"]
    assert "Otitis" in body["structured_data"]["clinical"]["history"]

    record_id = body["id"]
    listed = client.get("/api/records")
    assert listed.status_code == 200
    assert any(item["id"] == record_id for item in listed.json()["items"])

    detail = client.get(f"/api/records/{record_id}")
    assert detail.status_code == 200
    assert detail.json().get("processing") is None

    file_resp = client.get(f"/api/records/{record_id}/file")
    assert file_resp.status_code == 200
    assert file_resp.headers["content-type"].startswith("application/pdf")


def test_upload_docx_and_structure(client: TestClient) -> None:
    docx_bytes = make_sample_docx_bytes()
    response = client.post(
        "/api/records",
        files={
            "file": (
                "buddy.docx",
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "completed"
    assert body["content_type"] == (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    assert "Buddy" in (body["raw_text"] or "")
    assert body["structured_data"]["pet"]["name"] == "Buddy"

    file_resp = client.get(f"/api/records/{body['id']}/file")
    assert file_resp.status_code == 200
    assert file_resp.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )


def test_reject_unsupported_format(client: TestClient) -> None:
    response = client.post(
        "/api/records",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_reject_legacy_doc(client: TestClient) -> None:
    response = client.post(
        "/api/records",
        files={"file": ("legacy.doc", b"hello", "application/msword")},
    )
    assert response.status_code == 400
    assert "docx" in response.json()["detail"].lower()


def test_patch_structured_data(client: TestClient) -> None:
    pdf_bytes = make_sample_pdf_bytes()
    created = client.post(
        "/api/records",
        files={"file": ("buddy.pdf", pdf_bytes, "application/pdf")},
    ).json()

    payload = created["structured_data"]
    payload["pet"]["name"] = "Buddy Updated"
    patched = client.patch(
        f"/api/records/{created['id']}",
        json={"structured_data": payload},
    )
    assert patched.status_code == 200
    assert patched.json()["structured_data"]["pet"]["name"] == "Buddy Updated"


def test_pdfplumber_extractor(tmp_path: Path) -> None:
    from app.adapters.pdf_extractor import PdfplumberExtractor

    pdf_path = tmp_path / "sample.pdf"
    pdf_path.write_bytes(make_sample_pdf_bytes())
    text = PdfplumberExtractor().extract(pdf_path)
    assert "Buddy" in text
    assert "Otitis" in text
