from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from letai_factbase.db.session import init_db
from letai_factbase.main import app


def _make_ocr_png(path: Path) -> bytes:
    image = Image.new("RGB", (900, 260), color="white")
    draw = ImageDraw.Draw(image)
    font_path = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
    font = ImageFont.truetype(str(font_path), 52) if font_path.exists() else ImageFont.load_default()
    draw.text((60, 80), "Test OCR 123", fill="black", font=font)
    image.save(path)
    return path.read_bytes()


def test_run_ocr_creates_blocks_and_evidence() -> None:
    init_db()
    client = TestClient(app)
    png_bytes = _make_ocr_png(Path("/private/tmp/letai-ocr-run-test.png"))

    import_response = client.post(
        "/api/sources/import",
        files={"file": ("ocr-run-test.png", png_bytes, "image/png")},
        data={"title": "OCR Run Test PNG", "imported_by": "pytest", "authority_level": "99"},
    )
    assert import_response.status_code == 200
    source_uid = import_response.json()["source_uid"]

    render_response = client.post(f"/api/sources/{source_uid}/render-pages")
    assert render_response.status_code == 200

    pages_response = client.get("/api/ocr-pages")
    pages = [page for page in pages_response.json() if page["source_uid"] == source_uid]
    assert pages
    ocr_page_uid = pages[0]["ocr_page_uid"]

    ocr_response = client.post(f"/api/ocr-pages/{ocr_page_uid}/run-ocr")
    assert ocr_response.status_code == 200
    assert ocr_response.json()["blocks_created"] >= 1

    blocks_response = client.get("/api/ocr-blocks")
    blocks = [block for block in blocks_response.json() if block["ocr_page_uid"] == ocr_page_uid]
    assert blocks
    assert any("OCR" in block["text"] or "123" in block["text"] for block in blocks)

    evidence_response = client.get("/api/evidence")
    evidence = [item for item in evidence_response.json() if item["ocr_page_uid"] == ocr_page_uid]
    assert evidence
    assert "bbox" in evidence[0]["locator_json"]
