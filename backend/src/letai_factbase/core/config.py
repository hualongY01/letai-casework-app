from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"
    db_path: Path = Path("./storage/letai_factbase.sqlite3")
    storage_root: Path = Path("./storage")
    vault_export_dir: Path = Path("./storage/vault_readonly")
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_api_base: str = "https://api.openai.com/v1"
    llm_model: str = ""
    llm_timeout_seconds: int = 60
    llm_max_candidates: int = 8

    model_config = SettingsConfigDict(
        env_prefix="LETAI_",
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
