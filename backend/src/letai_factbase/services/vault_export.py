from pathlib import Path

from sqlmodel import Session, select

from letai_factbase.models import FactCard


def export_confirmed_facts(session: Session, export_dir: Path) -> list[Path]:
    facts_dir = export_dir / "facts"
    facts_dir.mkdir(parents=True, exist_ok=True)
    exported: list[Path] = []
    facts = session.exec(select(FactCard)).all()
    for fact in facts:
        path = facts_dir / f"{fact.fc_uid}-v{fact.version}.md"
        content = (
            "---\n"
            f"id: {fact.fc_uid}\n"
            f"version: {fact.version}\n"
            f"status: {fact.status.value}\n"
            f"source: {fact.source_uid}\n"
            f"evidence: {fact.evidence_uid}\n"
            "readonly: true\n"
            "---\n\n"
            f"# {fact.fc_uid} v{fact.version}\n\n"
            f"{fact.fact_text}\n"
        )
        path.write_text(content, encoding="utf-8")
        exported.append(path)
    return exported

