from typing import Optional
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from letai_factbase.db.session import get_session, init_db
from letai_factbase.models import (
    DocumentChunk,
    EvidenceSpan,
    FactCard,
    FactCandidate,
    FactRequest,
    LLMCallLog,
    OCRBlock,
    OCRPage,
    Source,
)
from letai_factbase.schemas import (
    AgentContextPack,
    ExtractCandidatesResponse,
    FactCandidateCreate,
    FactConfirmationRequest,
    ParseSourceResponse,
    RenderPagesResponse,
    RunOCRResponse,
    SourceImportResponse,
)
from letai_factbase.services.candidates import create_fact_candidate
from letai_factbase.services.fact_gateway import build_context_pack
from letai_factbase.services.importer import import_upload
from letai_factbase.services.llm_extractor import (
    LLMClientError,
    LLMNotConfiguredError,
    extract_candidates_from_chunk,
)
from letai_factbase.services.ocr import run_ocr_for_page
from letai_factbase.services.page_renderer import render_source_pages
from letai_factbase.services.parser import parse_source_file
from letai_factbase.services.review import confirm_candidate

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/admin/init-db")
def initialize_database() -> dict[str, str]:
    init_db()
    return {"status": "initialized"}


@router.post("/sources/import", response_model=SourceImportResponse)
async def import_source(
    file: UploadFile = File(...),
    title: Optional[str] = Form(default=None),
    imported_by: str = Form(default="system"),
    authority_level: int = Form(default=99),
    session: Session = Depends(get_session),
) -> Source:
    return await import_upload(
        session=session,
        upload=file,
        title=title,
        imported_by=imported_by,
        authority_level=authority_level,
    )


@router.get("/sources")
def list_sources(session: Session = Depends(get_session)) -> list[Source]:
    return list(session.exec(select(Source)).all())


@router.post("/sources/{source_uid}/parse", response_model=ParseSourceResponse)
def parse_source(
    source_uid: str,
    force: bool = False,
    session: Session = Depends(get_session),
) -> ParseSourceResponse:
    try:
        chunks = parse_source_file(session, source_uid, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ParseSourceResponse(source_uid=source_uid, chunks_created=len(chunks))


@router.post("/sources/{source_uid}/render-pages", response_model=RenderPagesResponse)
def render_pages(
    source_uid: str,
    force: bool = False,
    session: Session = Depends(get_session),
) -> RenderPagesResponse:
    try:
        pages = render_source_pages(session, source_uid, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RenderPagesResponse(source_uid=source_uid, pages_created=len(pages))


@router.get("/chunks")
def list_chunks(session: Session = Depends(get_session)) -> list[DocumentChunk]:
    return list(session.exec(select(DocumentChunk)).all())


@router.post("/chunks/{chunk_uid}/extract-candidates", response_model=ExtractCandidatesResponse)
def extract_chunk_candidates(
    chunk_uid: str,
    actor: str = "system",
    max_candidates: Optional[int] = None,
    session: Session = Depends(get_session),
) -> ExtractCandidatesResponse:
    try:
        return extract_candidates_from_chunk(
            session=session,
            chunk_uid=chunk_uid,
            actor=actor,
            max_candidates=max_candidates,
        )
    except LLMNotConfiguredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except LLMClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/evidence")
def list_evidence(session: Session = Depends(get_session)) -> list[EvidenceSpan]:
    return list(session.exec(select(EvidenceSpan)).all())


@router.get("/ocr-pages")
def list_ocr_pages(session: Session = Depends(get_session)) -> list[OCRPage]:
    return list(session.exec(select(OCRPage)).all())


@router.get("/ocr-pages/{ocr_page_uid}/image")
def get_ocr_page_image(
    ocr_page_uid: str,
    session: Session = Depends(get_session),
) -> FileResponse:
    page = session.exec(select(OCRPage).where(OCRPage.ocr_page_uid == ocr_page_uid)).first()
    if page is None:
        raise HTTPException(status_code=404, detail="OCR page not found")
    image_path = Path(page.page_image_path)
    if not image_path.exists():
        raise HTTPException(status_code=404, detail="OCR page image missing")
    return FileResponse(image_path, media_type="image/png")


@router.post("/ocr-pages/{ocr_page_uid}/run-ocr", response_model=RunOCRResponse)
def run_page_ocr(
    ocr_page_uid: str,
    force: bool = False,
    session: Session = Depends(get_session),
) -> RunOCRResponse:
    try:
        blocks = run_ocr_for_page(session, ocr_page_uid, force=force)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return RunOCRResponse(ocr_page_uid=ocr_page_uid, blocks_created=len(blocks))


@router.get("/ocr-blocks")
def list_ocr_blocks(session: Session = Depends(get_session)) -> list[OCRBlock]:
    return list(session.exec(select(OCRBlock)).all())


@router.get("/candidates")
def list_candidates(session: Session = Depends(get_session)) -> list[FactCandidate]:
    return list(session.exec(select(FactCandidate)).all())


@router.post("/candidates", response_model=FactCandidate)
def create_candidate(
    payload: FactCandidateCreate,
    session: Session = Depends(get_session),
) -> FactCandidate:
    try:
        return create_fact_candidate(session, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/candidates/confirm")
def confirm_fact_candidate(
    payload: FactConfirmationRequest,
    session: Session = Depends(get_session),
) -> FactCard:
    fact_card = confirm_candidate(session, payload)
    if fact_card is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return fact_card


@router.get("/facts")
def list_facts(session: Session = Depends(get_session)) -> list[FactCard]:
    return list(session.exec(select(FactCard)).all())


@router.get("/fact-requests/open")
def list_open_fact_requests(session: Session = Depends(get_session)) -> list[FactRequest]:
    statement = select(FactRequest).where(FactRequest.status == "open")
    return list(session.exec(statement).all())


@router.get("/llm-call-logs")
def list_llm_call_logs(session: Session = Depends(get_session)) -> list[LLMCallLog]:
    return list(session.exec(select(LLMCallLog)).all())


@router.get("/gateway/context-pack", response_model=AgentContextPack)
def context_pack(query: str, session: Session = Depends(get_session)) -> AgentContextPack:
    return build_context_pack(session, query)
