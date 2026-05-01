from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from shutil import copy2
from uuid import uuid4

from fastapi import UploadFile
from sqlmodel import Session

from letai_factbase.core.config import settings
from letai_factbase.models import Source


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def archive_source_file(path: Path) -> tuple[str, Path, str]:
    file_hash = file_sha256(path)
    source_uid = f"SRC-{uuid4().hex[:12]}"
    source_dir = settings.storage_root / "evidence_archive" / source_uid / "original"
    source_dir.mkdir(parents=True, exist_ok=True)
    archived_path = source_dir / path.name
    copy2(path, archived_path)
    return source_uid, archived_path, file_hash


def _bytes_sha256(content: bytes) -> str:
    return sha256(content).hexdigest()


async def import_upload(
    session: Session,
    upload: UploadFile,
    title: str | None = None,
    imported_by: str = "system",
    authority_level: int = 99,
) -> Source:
    content = await upload.read()
    source_uid = f"SRC-{uuid4().hex[:12]}"
    original_filename = upload.filename or "uploaded-file"
    file_hash = _bytes_sha256(content)

    source_dir = settings.storage_root / "evidence_archive" / source_uid / "original"
    source_dir.mkdir(parents=True, exist_ok=True)
    archive_path = source_dir / original_filename
    archive_path.write_bytes(content)

    source = Source(
        source_uid=source_uid,
        title=title or original_filename,
        original_filename=original_filename,
        archive_path=str(archive_path),
        file_hash=file_hash,
        mime_type=upload.content_type or "application/octet-stream",
        authority_level=authority_level,
        imported_by=imported_by,
    )
    session.add(source)
    session.commit()
    session.refresh(source)
    return source
