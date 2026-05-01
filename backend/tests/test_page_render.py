from pathlib import Path

import fitz
from fastapi.testclient import TestClient
from PIL import Image

from letai_factbase.db.session import init_db
from letai_factbase.main import app


def _make_render_pdf(path: Path) -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Page render test PDF")
    document.save(path)
    document.close()
    return path.read_bytes()


def _make_render_png(path: Path) -> bytes:
    image = Image.new("RGB", (320, 180), color="white")
    image.save(path)
    return path.read_bytes()


def test_pdf_render_pages_creates_ocr_page_record() -> None:
    init_db()
    client = TestClient(app)
    pdf_bytes = _make_render_pdf(Path("/private/tmp/letai-render-test.pdf"))

    import_response = client.post(
        "/api/sources/import",
        files={"file": ("render-test.pdf", pdf_bytes, "application/pdf")},
        data={"title": "Render Test PDF", "imported_by": "pytest", "authority_level": "99"},
    )
    assert import_response.status_code == 200
    source_uid = import_response.json()["source_uid"]

    render_response = client.post(f"/api/sources/{source_uid}/render-pages")

    assert render_response.status_code == 200
    assert render_response.json()["pages_created"] == 1

    pages_response = client.get("/api/ocr-pages")
    pages = [page for page in pages_response.json() if page["source_uid"] == source_uid]
    assert len(pages) == 1
    assert pages[0]["page_number"] == 1
    assert Path(pages[0]["page_image_path"]).exists()
    assert pages[0]["page_image_hash"]

    image_response = client.get(f"/api/ocr-pages/{pages[0]['ocr_page_uid']}/image")
    assert image_response.status_code == 200
    assert image_response.headers["content-type"] == "image/png"


def test_image_render_pages_normalizes_to_page_png() -> None:
    init_db()
    client = TestClient(app)
    png_bytes = _make_render_png(Path("/private/tmp/letai-render-test.png"))

    import_response = client.post(
        "/api/sources/import",
        files={"file": ("render-test.png", png_bytes, "image/png")},
        data={"title": "Render Test PNG", "imported_by": "pytest", "authority_level": "99"},
    )
    assert import_response.status_code == 200
    source_uid = import_response.json()["source_uid"]

    render_response = client.post(f"/api/sources/{source_uid}/render-pages")

    assert render_response.status_code == 200
    assert render_response.json()["pages_created"] == 1
