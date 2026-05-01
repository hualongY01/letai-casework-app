from fastapi.testclient import TestClient

from letai_factbase.db.session import init_db
from letai_factbase.main import app


def test_create_and_confirm_candidate_from_evidence() -> None:
    init_db()
    client = TestClient(app)
    text = "Candidate test: the test entity amount is 1 million CNY.".encode("utf-8")

    import_response = client.post(
        "/api/sources/import",
        files={"file": ("candidate-flow-test.txt", text, "text/plain")},
        data={
            "title": "Candidate Flow Test Source",
            "imported_by": "pytest",
            "authority_level": "99",
        },
    )
    assert import_response.status_code == 200
    source_uid = import_response.json()["source_uid"]

    parse_response = client.post(f"/api/sources/{source_uid}/parse")
    assert parse_response.status_code == 200

    evidence_response = client.get("/api/evidence")
    evidence = [item for item in evidence_response.json() if item["source_uid"] == source_uid][0]

    candidate_response = client.post(
        "/api/candidates",
        json={
            "source_uid": source_uid,
            "evidence_uid": evidence["evidence_uid"],
            "original_candidate_text": evidence["excerpt"],
            "proposed_fact_text": "The test entity amount is 1 million CNY.",
            "fact_type": "amount",
            "tags": ["test", "waterfall_input"],
            "llm_model": None,
            "prompt_version": None,
        },
    )
    assert candidate_response.status_code == 200
    candidate = candidate_response.json()
    assert candidate["status"] == "pending_review"

    confirm_response = client.post(
        "/api/candidates/confirm",
        json={
            "candidate_uid": candidate["candidate_uid"],
            "confirmed_fact_text": "The test entity amount is CNY 1 million.",
            "confirmed_by": "pytest",
            "edit_reason": "Clarified currency wording",
        },
    )
    assert confirm_response.status_code == 200
    fact = confirm_response.json()
    assert fact["candidate_uid"] == candidate["candidate_uid"]
    assert fact["edited_from_candidate"] is True
    assert fact["edit_reason"] == "Clarified currency wording"
