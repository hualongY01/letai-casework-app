import json
import urllib.error
import urllib.request
from datetime import datetime
from typing import Any, Optional, Protocol
from uuid import uuid4

from sqlmodel import Session, select

from letai_factbase.core.config import settings
from letai_factbase.models import DocumentChunk, EvidenceSpan, FactCandidate, LLMCallLog
from letai_factbase.schemas import ExtractCandidatesResponse, FactCandidateCreate
from letai_factbase.services.candidates import create_fact_candidate
from letai_factbase.services.redaction import redact_sensitive_text


PROMPT_VERSION = "fact_candidate_extraction_v0.1"


class LLMNotConfiguredError(RuntimeError):
    pass


class LLMClientError(RuntimeError):
    pass


class FactExtractionClient(Protocol):
    provider: str
    model: str

    def extract(self, prompt: str, max_candidates: int) -> dict[str, Any]:
        ...


class OpenAIResponsesClient:
    provider = "openai"

    def __init__(
        self,
        api_key: str,
        model: str,
        api_base: str = "https://api.openai.com/v1",
        timeout_seconds: int = 60,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self.api_base = api_base.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def extract(self, prompt: str, max_candidates: int) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "instructions": _system_instructions(),
            "input": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt,
                        }
                    ],
                }
            ],
            "max_output_tokens": 2500,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "fact_candidate_extraction",
                    "strict": True,
                    "schema": _output_schema(),
                }
            },
        }
        request = urllib.request.Request(
            f"{self.api_base}/responses",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_seconds) as response:
                response_body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise LLMClientError(f"OpenAI API error {exc.code}: {error_body}") from exc
        except urllib.error.URLError as exc:
            raise LLMClientError(f"OpenAI API connection error: {exc}") from exc

        data = json.loads(response_body)
        output_text = _extract_output_text(data)
        try:
            return json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise LLMClientError("OpenAI response did not contain valid JSON") from exc


def extract_candidates_from_chunk(
    session: Session,
    chunk_uid: str,
    actor: str = "system",
    max_candidates: Optional[int] = None,
    client: Optional[FactExtractionClient] = None,
) -> ExtractCandidatesResponse:
    chunk = session.exec(select(DocumentChunk).where(DocumentChunk.chunk_uid == chunk_uid)).first()
    if chunk is None:
        raise ValueError(f"Chunk not found: {chunk_uid}")
    evidence = session.exec(
        select(EvidenceSpan).where(EvidenceSpan.chunk_uid == chunk_uid)
    ).first()
    if evidence is None:
        raise ValueError(f"Evidence not found for chunk: {chunk_uid}")

    llm_client = client or _client_from_settings()
    candidate_limit = max_candidates or settings.llm_max_candidates
    redaction = redact_sensitive_text(chunk.text)
    prompt = _build_prompt(
        source_uid=chunk.source_uid,
        chunk_uid=chunk.chunk_uid,
        redacted_chunk_text=redaction.text,
        max_candidates=candidate_limit,
    )
    log = LLMCallLog(
        llm_call_uid=f"LLM-{uuid4().hex[:12]}",
        provider=llm_client.provider,
        source_uid=chunk.source_uid,
        chunk_uid=chunk.chunk_uid,
        prompt_version=PROMPT_VERSION,
        model=llm_client.model,
        input_text_redacted=redaction.text,
        redaction_summary_json=json.dumps(redaction.summary, ensure_ascii=False),
        status="started",
    )
    session.add(log)
    session.commit()
    session.refresh(log)

    try:
        extraction = llm_client.extract(prompt, candidate_limit)
        normalized_facts = _normalize_facts(extraction.get("facts", []), candidate_limit)
        created: list[FactCandidate] = []
        skipped_duplicates = 0
        for fact in normalized_facts:
            if _candidate_exists(
                session=session,
                evidence_uid=evidence.evidence_uid,
                proposed_fact_text=fact["proposed_fact_text"],
                model=llm_client.model,
                prompt_version=PROMPT_VERSION,
            ):
                skipped_duplicates += 1
                continue
            created.append(
                create_fact_candidate(
                    session=session,
                    payload=FactCandidateCreate(
                        source_uid=chunk.source_uid,
                        evidence_uid=evidence.evidence_uid,
                        original_candidate_text=fact.get("supporting_quote") or evidence.excerpt,
                        proposed_fact_text=fact["proposed_fact_text"],
                        fact_type=fact["fact_type"],
                        tags=fact["tags"],
                        llm_model=llm_client.model,
                        prompt_version=PROMPT_VERSION,
                    ),
                    actor=actor,
                )
            )
        log.output_json = json.dumps(extraction, ensure_ascii=False)
        log.output_text = log.output_json
        log.status = "succeeded"
        log.completed_at = datetime.utcnow()
        session.add(log)
        session.commit()
        session.refresh(log)
        return ExtractCandidatesResponse(
            chunk_uid=chunk.chunk_uid,
            source_uid=chunk.source_uid,
            evidence_uid=evidence.evidence_uid,
            llm_call_uid=log.llm_call_uid,
            prompt_version=PROMPT_VERSION,
            model=llm_client.model,
            candidates_created=len(created),
            skipped_duplicates=skipped_duplicates,
            redaction_summary=redaction.summary,
        )
    except Exception as exc:
        log.status = "failed"
        log.error_message = str(exc)
        log.completed_at = datetime.utcnow()
        session.add(log)
        session.commit()
        raise


def _client_from_settings() -> OpenAIResponsesClient:
    if not settings.llm_api_key:
        raise LLMNotConfiguredError("LETAI_LLM_API_KEY is not configured")
    if not settings.llm_model:
        raise LLMNotConfiguredError("LETAI_LLM_MODEL is not configured")
    if settings.llm_provider != "openai":
        raise LLMNotConfiguredError(f"Unsupported LLM provider: {settings.llm_provider}")
    return OpenAIResponsesClient(
        api_key=settings.llm_api_key,
        model=settings.llm_model,
        api_base=settings.llm_api_base,
        timeout_seconds=settings.llm_timeout_seconds,
    )


def _system_instructions() -> str:
    return (
        "You are the candidate-fact extractor for the Letai local factbase. "
        "Extract only objective candidate facts from the provided SOURCE_CHUNK. "
        "Do not use external knowledge. Do not fill in missing dates, amounts, people, "
        "file names, or legal conclusions. Each candidate must be directly supported "
        "by supporting_quote. Do not create confirmed facts; create only FactCandidate "
        "items for human review. If the source is insufficient, return an empty facts array."
    )


def _build_prompt(
    source_uid: str,
    chunk_uid: str,
    redacted_chunk_text: str,
    max_candidates: int,
) -> str:
    return (
        f"SOURCE_ID: {source_uid}\n"
        f"CHUNK_ID: {chunk_uid}\n"
        f"PROMPT_VERSION: {PROMPT_VERSION}\n"
        f"MAX_CANDIDATES: {max_candidates}\n\n"
        "Allowed FACT_TYPES: entity, date, amount, procedure, asset, liability, contract, "
        "court_document, operation, risk_marker, other.\n"
        "Use generic tags or Letai-specific tags, for example restructuring, icbc_asia, "
        "cash_package, asset_valuation, daily_report, ocr, letai.\n\n"
        "SOURCE_CHUNK_BEGIN\n"
        f"{redacted_chunk_text}\n"
        "SOURCE_CHUNK_END"
    )


def _output_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "facts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "proposed_fact_text": {
                            "type": "string",
                            "description": "Objective candidate fact directly supported by the source text.",
                        },
                        "fact_type": {
                            "type": "string",
                            "enum": [
                                "entity",
                                "date",
                                "amount",
                                "procedure",
                                "asset",
                                "liability",
                                "contract",
                                "court_document",
                                "operation",
                                "risk_marker",
                                "other",
                            ],
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "supporting_quote": {
                            "type": "string",
                            "description": "Short quote from SOURCE_CHUNK that directly supports the candidate fact.",
                        },
                    },
                    "required": [
                        "proposed_fact_text",
                        "fact_type",
                        "tags",
                        "supporting_quote",
                    ],
                },
            }
        },
        "required": ["facts"],
    }


def _extract_output_text(data: dict[str, Any]) -> str:
    output_text = data.get("output_text")
    if isinstance(output_text, str) and output_text.strip():
        return output_text
    for output_item in data.get("output", []):
        if output_item.get("type") != "message":
            continue
        for content_item in output_item.get("content", []):
            if content_item.get("type") in {"output_text", "text"}:
                text = content_item.get("text")
                if isinstance(text, str) and text.strip():
                    return text
    raise LLMClientError("OpenAI response did not include output text")


def _normalize_facts(raw_facts: Any, max_candidates: int) -> list[dict[str, Any]]:
    if not isinstance(raw_facts, list):
        return []
    normalized: list[dict[str, Any]] = []
    for item in raw_facts[:max_candidates]:
        if not isinstance(item, dict):
            continue
        proposed = str(item.get("proposed_fact_text", "")).strip()
        supporting_quote = str(item.get("supporting_quote", "")).strip()
        fact_type = str(item.get("fact_type", "other")).strip() or "other"
        tags = item.get("tags", [])
        if not proposed or not supporting_quote:
            continue
        if not isinstance(tags, list):
            tags = []
        normalized.append(
            {
                "proposed_fact_text": proposed,
                "fact_type": fact_type,
                "tags": [str(tag).strip() for tag in tags if str(tag).strip()],
                "supporting_quote": supporting_quote,
            }
        )
    return normalized


def _candidate_exists(
    session: Session,
    evidence_uid: str,
    proposed_fact_text: str,
    model: str,
    prompt_version: str,
) -> bool:
    statement = (
        select(FactCandidate)
        .where(FactCandidate.evidence_uid == evidence_uid)
        .where(FactCandidate.proposed_fact_text == proposed_fact_text)
        .where(FactCandidate.llm_model == model)
        .where(FactCandidate.prompt_version == prompt_version)
    )
    return session.exec(statement).first() is not None
