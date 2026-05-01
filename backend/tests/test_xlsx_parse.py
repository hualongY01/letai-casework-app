from pathlib import Path

from fastapi.testclient import TestClient
from openpyxl import Workbook

from letai_factbase.db.session import init_db
from letai_factbase.main import app


def _make_xlsx(path: Path) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Claims"
    sheet.append(["Entity", "Amount", "Description"])
    sheet.append(["Letai Test Entity", 1200000, "Validates Excel row parsing"])
    workbook.save(path)
    workbook.close()
    return path.read_bytes()


def test_xlsx_parse_preserves_sheet_and_row_metadata() -> None:
    init_db()
    client = TestClient(app)
    xlsx_bytes = _make_xlsx(Path("/private/tmp/letai-xlsx-parse-test.xlsx"))

    import_response = client.post(
        "/api/sources/import",
        files={
            "file": (
                "xlsx-parse-test.xlsx",
                xlsx_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        data={
            "title": "XLSX Parse Test Source",
            "imported_by": "pytest",
            "authority_level": "99",
        },
    )
    assert import_response.status_code == 200
    source_uid = import_response.json()["source_uid"]

    parse_response = client.post(f"/api/sources/{source_uid}/parse")

    assert parse_response.status_code == 200
    assert parse_response.json()["chunks_created"] >= 2

    chunks_response = client.get("/api/chunks")
    chunks = [chunk for chunk in chunks_response.json() if chunk["source_uid"] == source_uid]
    data_rows = [chunk for chunk in chunks if "Letai Test Entity" in chunk["text"]]
    assert data_rows
    assert data_rows[0]["sheet_name"] == "Claims"
    assert data_rows[0]["row_start"] == 2
