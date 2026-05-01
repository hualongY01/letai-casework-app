from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from uuid import uuid4

import pytesseract
from PIL import Image
from sqlmodel import Session, select

from letai_factbase.models import EvidenceSpan, FactCandidate, FactCard, OCRBlock, OCRPage

@dataclass(frozen=True)
class OCRBlockResult:
    text: str
    confidence: float
    bbox: dict[str, float]


@dataclass(frozen=True)
class OCRPageResult:
    page_number: int
    image_path: Path
    image_hash: str
    blocks: list[OCRBlockResult]


class LocalOCREngine:
    """Local OCR adapter backed by Tesseract.

    This is intentionally local-only. It does not upload page images to any
    cloud multimodal model.
    """

    engine_name = "tesseract-local"

    def __init__(self, language: str = "chi_sim+eng") -> None:
        self.language = language

    def run_on_image(self, image_path: Path) -> list[OCRBlockResult]:
        with Image.open(image_path) as image:
            data = pytesseract.image_to_data(
                image,
                lang=self.language,
                output_type=pytesseract.Output.DICT,
            )

        blocks: list[OCRBlockResult] = []
        for index, text in enumerate(data.get("text", [])):
            clean_text = text.strip()
            if not clean_text:
                continue
            confidence = _parse_confidence(data["conf"][index])
            if confidence < 0:
                continue
            blocks.append(
                OCRBlockResult(
                    text=clean_text,
                    confidence=confidence / 100,
                    bbox={
                        "x": float(data["left"][index]),
                        "y": float(data["top"][index]),
                        "width": float(data["width"][index]),
                        "height": float(data["height"][index]),
                    },
                )
            )
        return blocks


def _parse_confidence(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0


def run_ocr_for_page(
    session: Session,
    ocr_page_uid: str,
    engine: LocalOCREngine | None = None,
    force: bool = False,
) -> list[OCRBlock]:
    page = session.exec(select(OCRPage).where(OCRPage.ocr_page_uid == ocr_page_uid)).first()
    if page is None:
        raise ValueError(f"OCR page not found: {ocr_page_uid}")
    existing_blocks = _get_existing_blocks(session, ocr_page_uid)
    if existing_blocks and not force:
        return existing_blocks
    if existing_blocks and force:
        _delete_existing_ocr_outputs(session, ocr_page_uid)

    ocr_engine = engine or LocalOCREngine()
    results = ocr_engine.run_on_image(Path(page.page_image_path))
    created_blocks: list[OCRBlock] = []

    for result in results:
        block_uid = f"OCRBLOCK-{uuid4().hex[:12]}"
        evidence_uid = f"EVID-{uuid4().hex[:12]}"
        bbox_json = json.dumps(result.bbox, ensure_ascii=False)
        block = OCRBlock(
            ocr_block_uid=block_uid,
            ocr_page_uid=ocr_page_uid,
            text=result.text,
            confidence=result.confidence,
            bbox_json=bbox_json,
        )
        evidence = EvidenceSpan(
            evidence_uid=evidence_uid,
            source_uid=page.source_uid,
            ocr_page_uid=ocr_page_uid,
            excerpt=result.text,
            locator_json=json.dumps(
                {
                    "source_uid": page.source_uid,
                    "ocr_page_uid": ocr_page_uid,
                    "ocr_block_uid": block_uid,
                    "page_number": page.page_number,
                    "bbox": result.bbox,
                    "ocr_engine": ocr_engine.engine_name,
                    "ocr_confidence": result.confidence,
                    "parser": "ocr",
                },
                ensure_ascii=False,
            ),
            confidence=result.confidence,
        )
        session.add(block)
        session.add(evidence)
        created_blocks.append(block)

    page.ocr_engine = ocr_engine.engine_name
    session.add(page)
    session.commit()
    for block in created_blocks:
        session.refresh(block)
    return created_blocks


def _get_existing_blocks(session: Session, ocr_page_uid: str) -> list[OCRBlock]:
    return list(session.exec(select(OCRBlock).where(OCRBlock.ocr_page_uid == ocr_page_uid)).all())


def _delete_existing_ocr_outputs(session: Session, ocr_page_uid: str) -> None:
    evidence = list(
        session.exec(select(EvidenceSpan).where(EvidenceSpan.ocr_page_uid == ocr_page_uid)).all()
    )
    evidence_uids = [item.evidence_uid for item in evidence]
    if evidence_uids and _has_evidence_dependencies(session, evidence_uids):
        raise ValueError("Cannot force OCR: existing OCR evidence is referenced by candidates or FCs")

    blocks = _get_existing_blocks(session, ocr_page_uid)
    for item in evidence:
        session.delete(item)
    for block in blocks:
        session.delete(block)
    session.flush()


def _has_evidence_dependencies(session: Session, evidence_uids: list[str]) -> bool:
    candidate = session.exec(
        select(FactCandidate).where(FactCandidate.evidence_uid.in_(evidence_uids))
    ).first()
    if candidate is not None:
        return True
    fact = session.exec(select(FactCard).where(FactCard.evidence_uid.in_(evidence_uids))).first()
    return fact is not None
