from pathlib import Path

from fastapi.testclient import TestClient

from letai_factbase.db.session import init_db
from letai_factbase.main import app


def test_source_import_creates_source_record() -> None:
    init_db()
    client = TestClient(app)
    payload = "Test material for source import automation.".encode("utf-8")

    response = client.post(
        "/api/sources/import",
        files={"file": ("source-import-test.txt", payload, "text/plain")},
        data={
            "title": "Source Import Test",
            "imported_by": "pytest",
            "authority_level": "99",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Source Import Test"
    assert body["original_filename"] == "source-import-test.txt"
    assert body["file_hash"]
    assert Path(body["archive_path"]).exists()
