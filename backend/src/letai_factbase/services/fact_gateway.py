from sqlmodel import Session, select

from letai_factbase.models import ConflictRecord, EvidenceSpan, FactCard, FactRequest
from letai_factbase.schemas import AgentContextPack


def build_context_pack(session: Session, query: str) -> AgentContextPack:
    facts = list(session.exec(select(FactCard).limit(20)).all())
    open_frs = list(session.exec(select(FactRequest).where(FactRequest.status == "open")).all())
    conflicts = list(session.exec(select(ConflictRecord).limit(20)).all())
    evidence_uids = [fact.evidence_uid for fact in facts]
    evidence = []
    if evidence_uids:
        evidence = list(
            session.exec(select(EvidenceSpan).where(EvidenceSpan.evidence_uid.in_(evidence_uids))).all()
        )

    return AgentContextPack(
        query=query,
        facts=[fact.model_dump() for fact in facts],
        open_fact_requests=[fr.model_dump() for fr in open_frs],
        conflicts=[conflict.model_dump() for conflict in conflicts],
        evidence=[item.model_dump() for item in evidence],
    )

