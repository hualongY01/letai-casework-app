from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Locator(BaseModel):
    source_uid: str
    page_number: Optional[int] = None
    sheet_name: Optional[str] = None
    row_start: Optional[int] = None
    row_end: Optional[int] = None
    bbox: Optional[Dict[str, float]] = None


class FactCandidateCreate(BaseModel):
    source_uid: str
    evidence_uid: str
    original_candidate_text: str
    proposed_fact_text: str
    fact_type: str
    tags: List[str] = Field(default_factory=list)
    llm_model: Optional[str] = None
    prompt_version: Optional[str] = None


class FactConfirmationRequest(BaseModel):
    candidate_uid: str
    confirmed_fact_text: str
    confirmed_by: str
    edit_reason: Optional[str] = None


class SourceImportResponse(BaseModel):
    source_uid: str
    title: str
    original_filename: str
    archive_path: str
    file_hash: str
    mime_type: str
    status: str
    version: int


class ParseSourceResponse(BaseModel):
    source_uid: str
    chunks_created: int


class RenderPagesResponse(BaseModel):
    source_uid: str
    pages_created: int


class RunOCRResponse(BaseModel):
    ocr_page_uid: str
    blocks_created: int


class ExtractCandidatesResponse(BaseModel):
    chunk_uid: str
    source_uid: str
    evidence_uid: str
    llm_call_uid: str
    prompt_version: str
    model: str
    candidates_created: int
    skipped_duplicates: int = 0
    redaction_summary: Dict[str, int] = Field(default_factory=dict)


class AgentContextPack(BaseModel):
    query: str
    facts: List[Dict[str, Any]] = Field(default_factory=list)
    open_fact_requests: List[Dict[str, Any]] = Field(default_factory=list)
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    usage_rules: List[str] = Field(
        default_factory=lambda: [
            "Only confirmed facts may be used as determinate facts.",
            "Evidence excerpts may be used for verification, not as confirmed facts.",
            "Open FR items must be described as missing or pending information.",
            "Conflicts must be presented as unresolved unless a resolution is recorded.",
        ]
    )
