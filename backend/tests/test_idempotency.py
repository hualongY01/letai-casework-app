from pathlib import Path

from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from letai_factbase.db.session import init_db
from letai_factbase.main import app


def _make_png(path: Path) -> bytes:
    image = Image.new("RGB", (900, 260), color="white")
    draw = ImageDraw.Draw(image)
    font_path = Path("/System/Library/Fonts/Supplemental/Arial.ttf")
    font = ImageFont.truetype(str(font_path), 52) if font_path.exists() else ImageFont.load_default()
    draw.text((60, 80), "Idempotent OCR 456", fill="black", font=font)
    image.save(path)
    return path.read_bytes()


def _import_text(client: TestClient) -> str:
    response = client.post(
        "/api/sources/import",
        files={"file": ("idempotent-parse.txt", b"Idempotent parse source.", "text/plain")},
        data={"title": "Idempotent Parse Source", "imported_by": "pytest", "authority_level": "99"},
    )
    assert response.status_code == 200
    return response.json()["source_uid"]


def _import_png(client: TestClient) -> str:
    png_bytes = _make_png(Path("/private/tmp/letai-idempotent-ocr.png"))
    response = client.post(
        "/api/sources/import",
        files={"file": ("idempotent-ocr.png", png_bytes, "image/png")},
        data={"title": "Idempotent OCR Source", "imported_by": "pytest", "authority_level": "99"},
    )
    assert response.status_code == 200
    return response.json()["source_uid"]


def test_parse_is_idempotent_by_default() -> None:
    init_db()
    client = TestClient(app)
    source_uid = _import_text(client)

    first = client.post(f"/api/sources/{source_uid}/parse")
    second = client.post(f"/api/sources/{source_uid}/parse")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["chunks_created"] == second.json()["chunks_created"]
    chunks = [chunk for chunk in client.get("/api/chunks").json() if chunk["source_uid"] == source_uid]
    assert len(chunks) == first.json()["chunks_created"]


def test_parse_force_rebuilds_without_dependencies() -> None:
    init_db()
    client = TestClient(app)
    source_uid = _import_text(client)

    client.post(f"/api/sources/{source_uid}/parse")
    before = [chunk for chunk in client.get("/api/chunks").json() if chunk["source_uid"] == source_uid]
    response = client.post(f"/api/sources/{source_uid}/parse?force=true")
    after = [chunk for chunk in client.get("/api/chunks").json() if chunk["source_uid"] == source_uid]

    assert response.status_code == 200
    assert len(after) == len(before)
    assert {chunk["chunk_uid"] for chunk in after} != {chunk["chunk_uid"] for chunk in before}


def test_parse_force_rejects_when_evidence_has_candidate_dependency() -> None:
    init_db()
    client = TestClient(app)
    source_uid = _import_text(client)

    client.post(f"/api/sources/{source_uid}/parse")
    evidence = [item for item in client.get("/api/evidence").json() if item["source_uid"] == source_uid][0]
    candidate_response = client.post(
        "/api/candidates",
        json={
            "source_uid": source_uid,
            "evidence_uid": evidence["evidence_uid"],
            "original_candidate_text": evidence["excerpt"],
            "proposed_fact_text": evidence["excerpt"],
            "fact_type": "test",
            "tags": ["idempotency"],
            "llm_model": None,
            "prompt_version": None,
        },
    )
    assert candidate_response.status_code == 200

    response = client.post(f"/api/sources/{source_uid}/parse?force=true")

    assert response.status_code == 409


def test_render_pages_is_idempotent_by_default() -> None:
    init_db()
    client = TestClient(app)
    source_uid = _import_png(client)

    first = client.post(f"/api/sources/{source_uid}/render-pages")
    second = client.post(f"/api/sources/{source_uid}/render-pages")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["pages_created"] == second.json()["pages_created"]
    pages = [page for page in client.get("/api/ocr-pages").json() if page["source_uid"] == source_uid]
    assert len(pages) == first.json()["pages_created"]


def test_ocr_is_idempotent_by_default() -> None:
    init_db()
    client = TestClient(app)
    source_uid = _import_png(client)
    client.post(f"/api/sources/{source_uid}/render-pages")
    page = [page for page in client.get("/api/ocr-pages").json() if page["source_uid"] == source_uid][0]

    first = client.post(f"/api/ocr-pages/{page['ocr_page_uid']}/run-ocr")
    second = client.post(f"/api/ocr-pages/{page['ocr_page_uid']}/run-ocr")

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["blocks_created"] == second.json()["blocks_created"]
    blocks = [
        block for block in client.get("/api/ocr-blocks").json() if block["ocr_page_uid"] == page["ocr_page_uid"]
    ]
    assert len(blocks) == first.json()["blocks_created"]
