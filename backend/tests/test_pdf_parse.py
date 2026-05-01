from pathlib import Path

import fitz
from fastapi.testclient import TestClient

from letai_factbase.db.session import init_db
from letai_factbase.main import app


def _make_pdf(path: Path) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "PDF test material for extractable-text parser validation.")
    page.insert_text((72, 104), "This file does not represent real case facts.")
    document.save(path)
    document.close()
    return path.read_bytes()


def test_pdf_parse_creates_page_located_chunks() -> None:
    init_db()
    client = TestClient(app)
    pdf_bytes = _make_pdf(Path("/private/tmp/letai-pdf-parse-test.pdf"))

    import_response = client.post(
        "/api/sources/import",
        files={"file": ("pdf-parse-test.pdf", pdf_bytes, "application/pdf")},
        data={
            "title": "PDF Parse Test Source",
            "imported_by": "pytest",
            "authority_level": "99",
        },
    )
    assert import_response.status_code == 200
    source_uid = import_response.json()["source_uid"]

    parse_response = client.post(f"/api/sources/{source_uid}/parse")

    assert parse_response.status_code == 200
    assert parse_response.json()["chunks_created"] >= 1

    chunks_response = client.get("/api/chunks")
    chunks = [chunk for chunk in chunks_response.json() if chunk["source_uid"] == source_uid]
    assert chunks
    assert chunks[0]["page_start"] == 1
    assert "extractable-text parser" in chunks[0]["text"]
