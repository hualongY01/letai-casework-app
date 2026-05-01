from __future__ import annotations

import json
from uuid import uuid4

from sqlmodel import Session, select

from letai_factbase.models import AuditLog, CandidateStatus, FactCard, FactCandidate
from letai_factbase.schemas import FactConfirmationRequest


def confirm_candidate(session: Session, payload: FactConfirmationRequest) -> FactCard | None:
    candidate = session.exec(
        select(FactCandidate).where(FactCandidate.candidate_uid == payload.candidate_uid)
    ).first()
    if candidate is None:
        return None

    edited = payload.confirmed_fact_text != candidate.original_candidate_text
    fact_card = FactCard(
        fc_uid=f"FC-{uuid4().hex[:12]}",
        version=1,
        fact_text=payload.confirmed_fact_text,
        fact_type=candidate.fact_type,
        tags_json=candidate.tags_json,
        source_uid=candidate.source_uid,
        evidence_uid=candidate.evidence_uid,
        candidate_uid=candidate.candidate_uid,
        edited_from_candidate=edited,
        edit_reason=payload.edit_reason,
        confirmed_by=payload.confirmed_by,
    )
    candidate.status = CandidateStatus.confirmed
    session.add(candidate)
    session.add(fact_card)
    session.add(
        AuditLog(
            actor=payload.confirmed_by,
            action="confirm_candidate",
            object_type="fact_candidate",
            object_uid=candidate.candidate_uid,
            details_json=json.dumps(
                {
                    "created_fc_uid": fact_card.fc_uid,
                    "edited_from_candidate": edited,
                    "edit_reason": payload.edit_reason,
                },
                ensure_ascii=False,
            ),
        )
    )
    session.commit()
    session.refresh(fact_card)
    return fact_card
