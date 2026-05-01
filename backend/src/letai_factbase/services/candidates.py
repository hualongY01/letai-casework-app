import json
from uuid import uuid4

from sqlmodel import Session, select

from letai_factbase.models import AuditLog, EvidenceSpan, FactCandidate
from letai_factbase.schemas import FactCandidateCreate


def create_fact_candidate(
    session: Session,
    payload: FactCandidateCreate,
    actor: str = "system",
) -> FactCandidate:
    evidence = session.exec(
        select(EvidenceSpan).where(EvidenceSpan.evidence_uid == payload.evidence_uid)
    ).first()
    if evidence is None:
        raise ValueError(f"Evidence not found: {payload.evidence_uid}")
    if evidence.source_uid != payload.source_uid:
        raise ValueError("Evidence source does not match candidate source")

    candidate = FactCandidate(
        candidate_uid=f"CAND-{uuid4().hex[:12]}",
        source_uid=payload.source_uid,
        evidence_uid=payload.evidence_uid,
        original_candidate_text=payload.original_candidate_text,
        proposed_fact_text=payload.proposed_fact_text,
        fact_type=payload.fact_type,
        tags_json=json.dumps(payload.tags, ensure_ascii=False),
        llm_model=payload.llm_model,
        prompt_version=payload.prompt_version,
    )
    session.add(candidate)
    session.add(
        AuditLog(
            actor=actor,
            action="create_fact_candidate",
            object_type="evidence",
            object_uid=payload.evidence_uid,
            details_json=json.dumps(
                {
                    "candidate_uid": candidate.candidate_uid,
                    "source_uid": payload.source_uid,
                    "fact_type": payload.fact_type,
                    "tags": payload.tags,
                },
                ensure_ascii=False,
            ),
        )
    )
    session.commit()
    session.refresh(candidate)
    return candidate
