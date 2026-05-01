from pathlib import Path

from sqlmodel import Session, SQLModel, create_engine

from letai_factbase.core.config import settings


def _database_url(db_path: Path) -> str:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{db_path}"


engine = create_engine(_database_url(settings.db_path), echo=False)


def init_db() -> None:
    # Import models before create_all so SQLModel metadata is populated.
    import letai_factbase.models  # noqa: F401

    SQLModel.metadata.create_all(engine)


def get_session() -> Session:
    with Session(engine) as session:
        yield session
