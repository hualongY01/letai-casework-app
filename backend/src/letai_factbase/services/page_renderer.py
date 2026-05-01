from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import fitz
from PIL import Image
from sqlmodel import Session, select

from letai_factbase.core.config import settings
from letai_factbase.models import EvidenceSpan, FactCandidate, FactCard, OCRBlock, OCRPage, Source


PDF_SUFFIXES = {".pdf"}
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def _file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _get_source(session: Session, source_uid: str) -> Source:
    source = session.exec(select(Source).where(Source.source_uid == source_uid)).first()
    if source is None:
        raise ValueError(f"Source not found: {source_uid}")
    return source


def render_source_pages(session: Session, source_uid: str, force: bool = False) -> list[OCRPage]:
    source = _get_source(session, source_uid)
    archive_path = Path(source.archive_path)
    suffix = archive_path.suffix.lower()
    pages_dir = settings.storage_root / "evidence_archive" / source_uid / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    existing_pages = _get_existing_pages(session, source_uid)
    if existing_pages and not force:
        return existing_pages
    if existing_pages and force:
        _delete_existing_render_outputs(session, source_uid, existing_pages)

    if suffix in PDF_SUFFIXES:
        pages = _render_pdf_pages(session, source_uid, archive_path, pages_dir)
    elif suffix in IMAGE_SUFFIXES:
        pages = [_render_image_page(session, source_uid, archive_path, pages_dir)]
    else:
        raise ValueError(f"Unsupported page rendering source type: {archive_path.suffix}")

    session.commit()
    for page in pages:
        session.refresh(page)
    return pages


def _get_existing_pages(session: Session, source_uid: str) -> list[OCRPage]:
    return list(session.exec(select(OCRPage).where(OCRPage.source_uid == source_uid)).all())


def _delete_existing_render_outputs(
    session: Session,
    source_uid: str,
    pages: list[OCRPage],
) -> None:
    page_uids = [page.ocr_page_uid for page in pages]
    evidence = list(
        session.exec(
            select(EvidenceSpan).where(
                EvidenceSpan.source_uid == source_uid,
                EvidenceSpan.ocr_page_uid.in_(page_uids),
            )
        ).all()
    )
    evidence_uids = [item.evidence_uid for item in evidence]
    if evidence_uids and _has_evidence_dependencies(session, evidence_uids):
        raise ValueError(
            "Cannot force render pages: existing OCR evidence is referenced by candidates or FCs"
        )

    blocks = list(
        session.exec(select(OCRBlock).where(OCRBlock.ocr_page_uid.in_(page_uids))).all()
    )
    for item in evidence:
        session.delete(item)
    for block in blocks:
        session.delete(block)
    for page in pages:
        session.delete(page)
    session.flush()


def _has_evidence_dependencies(session: Session, evidence_uids: list[str]) -> bool:
    candidate = session.exec(
        select(FactCandidate).where(FactCandidate.evidence_uid.in_(evidence_uids))
    ).first()
    if candidate is not None:
        return True
    fact = session.exec(select(FactCard).where(FactCard.evidence_uid.in_(evidence_uids))).first()
    return fact is not None


def _render_pdf_pages(
    session: Session,
    source_uid: str,
    archive_path: Path,
    pages_dir: Path,
) -> list[OCRPage]:
    pages: list[OCRPage] = []
    with fitz.open(archive_path) as document:
        for page_number, page in enumerate(document, start=1):
            pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
            page_path = pages_dir / f"page-{page_number:04d}.png"
            pixmap.save(page_path)
            pages.append(_create_ocr_page(session, source_uid, page_number, page_path))
    return pages


def _render_image_page(
    session: Session,
    source_uid: str,
    archive_path: Path,
    pages_dir: Path,
) -> OCRPage:
    page_path = pages_dir / "page-0001.png"
    with Image.open(archive_path) as image:
        image.convert("RGB").save(page_path)
    return _create_ocr_page(session, source_uid, 1, page_path)


def _create_ocr_page(
    session: Session,
    source_uid: str,
    page_number: int,
    page_path: Path,
) -> OCRPage:
    page = OCRPage(
        ocr_page_uid=f"OCRPAGE-{uuid4().hex[:12]}",
        source_uid=source_uid,
        page_number=page_number,
        page_image_path=str(page_path),
        page_image_hash=_file_sha256(page_path),
        ocr_engine="pending",
    )
    session.add(page)
    return page
