from fastapi.testclient import TestClient

from letai_factbase.db.session import init_db
from letai_factbase.main import app


def test_text_parse_creates_chunks_and_evidence() -> None:
    init_db()
    client = TestClient(app)
    text = "\n".join(
        [
            "Paragraph one: Letai test material.",
            "Paragraph two: validates chunk and evidence persistence.",
            "Paragraph three: does not represent real case facts.",
        ]
    ).encode("utf-8")

    import_response = client.post(
        "/api/sources/import",
        files={"file": ("parse-test.txt", text, "text/plain")},
        data={
            "title": "Parse Test Source",
            "imported_by": "pytest",
            "authority_level": "99",
        },
    )
    assert import_response.status_code == 200
    source_uid = import_response.json()["source_uid"]

    parse_response = client.post(f"/api/sources/{source_uid}/parse")

    assert parse_response.status_code == 200
    assert parse_response.json()["source_uid"] == source_uid
    assert parse_response.json()["chunks_created"] >= 1

    chunks_response = client.get("/api/chunks")
    evidence_response = client.get("/api/evidence")
    assert chunks_response.status_code == 200
    assert evidence_response.status_code == 200
    assert any(chunk["source_uid"] == source_uid for chunk in chunks_response.json())
    assert any(item["source_uid"] == source_uid for item in evidence_response.json())
