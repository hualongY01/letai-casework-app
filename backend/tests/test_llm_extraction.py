import json

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from letai_factbase.core.config import settings
from letai_factbase.db.session import engine, init_db
from letai_factbase.main import app
from letai_factbase.models import FactCandidate, LLMCallLog
from letai_factbase.services.llm_extractor import extract_candidates_from_chunk
from letai_factbase.services.redaction import redact_sensitive_text


class FakeExtractionClient:
    provider = "fake"
    model = "fake-fact-model"

    def __init__(self) -> None:
        self.prompts: list[str] = []

    def extract(self, prompt: str, max_candidates: int) -> dict:
        self.prompts.append(prompt)
        assert "13812345678" not in prompt
        assert "6222021234567890123" not in prompt
        return {
            "facts": [
                {
                    "proposed_fact_text": "测试主体联系电话为 [REDACTED_PHONE]。",
                    "fact_type": "entity",
                    "tags": ["test", "letai"],
                    "supporting_quote": "联系电话：[REDACTED_PHONE]",
                }
            ]
        }


def test_redact_sensitive_text_masks_common_personal_data() -> None:
    redacted = redact_sensitive_text(
        "张三，身份证号110101199003072211，电话13812345678，"
        "银行账号6222021234567890123，住址：北京市朝阳区测试路1号。"
    )
    assert "110101199003072211" not in redacted.text
    assert "13812345678" not in redacted.text
    assert "6222021234567890123" not in redacted.text
    assert "北京市朝阳区测试路1号" not in redacted.text
    assert redacted.summary["id_number"] == 1
    assert redacted.summary["phone_number"] == 1
    assert redacted.summary["bank_account"] == 1
    assert redacted.summary["address_label"] == 1


def test_extract_candidates_from_chunk_redacts_logs_and_deduplicates() -> None:
    init_db()
    client = TestClient(app)
    text = (
        "LLM提取测试：测试主体联系电话：13812345678，"
        "银行账号6222021234567890123，确认金额为100万元。"
    ).encode("utf-8")
    import_response = client.post(
        "/api/sources/import",
        files={"file": ("llm-extract-test.txt", text, "text/plain")},
        data={
            "title": "LLM Extract Test Source",
            "imported_by": "pytest",
            "authority_level": "99",
        },
    )
    assert import_response.status_code == 200
    source_uid = import_response.json()["source_uid"]
    assert client.post(f"/api/sources/{source_uid}/parse").status_code == 200

    chunk = [item for item in client.get("/api/chunks").json() if item["source_uid"] == source_uid][0]
    fake_client = FakeExtractionClient()
    with Session(engine) as session:
        response = extract_candidates_from_chunk(
            session=session,
            chunk_uid=chunk["chunk_uid"],
            actor="pytest",
            client=fake_client,
        )
        assert response.candidates_created == 1
        assert response.redaction_summary["phone_number"] == 1
        assert response.redaction_summary["bank_account"] == 1

        duplicate_response = extract_candidates_from_chunk(
            session=session,
            chunk_uid=chunk["chunk_uid"],
            actor="pytest",
            client=fake_client,
        )
        assert duplicate_response.candidates_created == 0
        assert duplicate_response.skipped_duplicates == 1

        candidates = session.exec(
            select(FactCandidate).where(FactCandidate.source_uid == source_uid)
        ).all()
        assert len(candidates) == 1
        assert candidates[0].status == "pending_review"

        logs = session.exec(
            select(LLMCallLog).where(LLMCallLog.source_uid == source_uid)
        ).all()
        assert len(logs) == 2
        assert all(log.status == "succeeded" for log in logs)
        assert "13812345678" not in logs[0].input_text_redacted
        assert json.loads(logs[0].output_json)["facts"][0]["fact_type"] == "entity"


def test_extract_candidates_endpoint_requires_llm_configuration(monkeypatch) -> None:
    init_db()
    monkeypatch.setattr(settings, "llm_api_key", "")
    monkeypatch.setattr(settings, "llm_model", "")
    client = TestClient(app)
    text = "未配置LLM时仍可导入解析，但不能自动提取候选事实。".encode("utf-8")
    import_response = client.post(
        "/api/sources/import",
        files={"file": ("llm-not-configured-test.txt", text, "text/plain")},
        data={"title": "LLM Not Configured Test Source"},
    )
    source_uid = import_response.json()["source_uid"]
    assert client.post(f"/api/sources/{source_uid}/parse").status_code == 200
    chunk = [item for item in client.get("/api/chunks").json() if item["source_uid"] == source_uid][0]

    extract_response = client.post(f"/api/chunks/{chunk['chunk_uid']}/extract-candidates")
    assert extract_response.status_code == 409
    assert "LETAI_LLM_API_KEY" in extract_response.json()["detail"]
