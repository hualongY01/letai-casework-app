from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class SourceStatus(str, Enum):
    active = "active"
    archived = "archived"
    superseded = "superseded"
    invalidated = "invalidated"
    missing = "missing"


class CandidateStatus(str, Enum):
    pending_review = "pending_review"
    confirmed = "confirmed"
    rejected = "rejected"
    needs_fr = "needs_fr"
    ocr_error = "ocr_error"


class FactStatus(str, Enum):
    current = "current"
    superseded = "superseded"
    retained = "retained"
    invalidated = "invalidated"


class ConflictResolution(str, Enum):
    unresolved = "unresolved"
    adopt_a = "adopt_a"
    adopt_b = "adopt_b"
    both_parallel = "both_parallel"
    needs_verification = "needs_verification"
    generated_fr = "generated_fr"


class Source(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    source_uid: str = Field(index=True, unique=True)
    title: str
    original_filename: str
    archive_path: str
    file_hash: str = Field(index=True)
    mime_type: str
    status: SourceStatus = Field(default=SourceStatus.active)
    version: int = Field(default=1)
    supersedes_source_uid: Optional[str] = Field(default=None, index=True)
    authority_level: int = Field(default=99)
    imported_at: datetime = Field(default_factory=datetime.utcnow)
    imported_by: str = Field(default="system")


class DocumentChunk(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    chunk_uid: str = Field(index=True, unique=True)
    source_uid: str = Field(index=True)
    text: str
    page_start: Optional[int] = None
    page_end: Optional[int] = None
    sheet_name: Optional[str] = None
    row_start: Optional[int] = None
    row_end: Optional[int] = None
    column_start: Optional[str] = None
    column_end: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OCRPage(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ocr_page_uid: str = Field(index=True, unique=True)
    source_uid: str = Field(index=True)
    page_number: int
    page_image_path: str
    page_image_hash: str
    ocr_engine: str
    created_at: datetime = Field(default_factory=datetime.utcnow)


class OCRBlock(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    ocr_block_uid: str = Field(index=True, unique=True)
    ocr_page_uid: str = Field(index=True)
    text: str
    confidence: float = Field(default=0.0)
    bbox_json: str


class EvidenceSpan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    evidence_uid: str = Field(index=True, unique=True)
    source_uid: str = Field(index=True)
    chunk_uid: Optional[str] = Field(default=None, index=True)
    ocr_page_uid: Optional[str] = Field(default=None, index=True)
    excerpt: str
    locator_json: str
    confidence: float = Field(default=1.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FactCandidate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_uid: str = Field(index=True, unique=True)
    source_uid: str = Field(index=True)
    evidence_uid: str = Field(index=True)
    original_candidate_text: str
    proposed_fact_text: str
    fact_type: str = Field(index=True)
    tags_json: str = Field(default="[]")
    status: CandidateStatus = Field(default=CandidateStatus.pending_review)
    llm_model: Optional[str] = None
    prompt_version: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FactCard(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fc_uid: str = Field(index=True)
    version: int = Field(default=1)
    status: FactStatus = Field(default=FactStatus.current)
    fact_text: str
    fact_type: str = Field(index=True)
    tags_json: str = Field(default="[]")
    source_uid: str = Field(index=True)
    evidence_uid: str = Field(index=True)
    candidate_uid: Optional[str] = Field(default=None, index=True)
    edited_from_candidate: bool = Field(default=False)
    edit_reason: Optional[str] = None
    confirmed_by: str
    confirmed_at: datetime = Field(default_factory=datetime.utcnow)
    supersedes_fc_uid: Optional[str] = Field(default=None, index=True)


class FactRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    fr_uid: str = Field(index=True, unique=True)
    question: str
    status: str = Field(default="open", index=True)
    related_entity: Optional[str] = Field(default=None, index=True)
    related_tags_json: str = Field(default="[]")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_reason: str


class ConflictRecord(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    conflict_uid: str = Field(index=True, unique=True)
    fact_a_uid: str
    fact_b_uid: str
    description: str
    resolution: ConflictResolution = Field(default=ConflictResolution.unresolved)
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None


class LLMCallLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    llm_call_uid: str = Field(index=True, unique=True)
    provider: str = Field(default="openai", index=True)
    source_uid: str = Field(index=True)
    chunk_uid: str = Field(index=True)
    prompt_version: str = Field(index=True)
    model: str = Field(index=True)
    input_text_redacted: str
    redaction_summary_json: str = Field(default="{}")
    output_text: str = Field(default="")
    output_json: str = Field(default="{}")
    status: str = Field(default="started", index=True)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class AuditLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    actor: str
    action: str
    object_type: str
    object_uid: str
    details_json: str = Field(default="{}")
    created_at: datetime = Field(default_factory=datetime.utcnow)
