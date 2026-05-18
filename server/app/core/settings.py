"""Application settings (env-driven via pydantic-settings)."""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


class Settings(BaseSettings):
    """Runtime configuration sourced from environment variables / `.env`."""

    model_config = SettingsConfigDict(
        env_file=(".env.dev", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    server_token: str = Field("change_me", alias="SERVER_TOKEN")
    host: str = Field("0.0.0.0", alias="BACKEND_HOST")
    port: int = Field(1030, alias="BACKEND_PORT")
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        "INFO", alias="LOG_LEVEL"
    )
    access_log_http: bool = Field(False, alias="ACCESS_LOG_HTTP")

    database_url: str = Field(
        f"sqlite+aiosqlite:///{DATA_DIR / 'remote-gtnh-control.sqlite'}",
        alias="DATABASE_URL",
    )
    sync_database_url: str = Field(
        f"sqlite:///{DATA_DIR / 'remote-gtnh-control.sqlite'}",
        alias="SYNC_DATABASE_URL",
    )
    nesql_database_url: str = Field(
        f"sqlite:///{DATA_DIR / 'nesql.sqlite'}",
        alias="NESQL_DATABASE_URL",
    )

    data_dir: Path = Field(default=DATA_DIR, alias="DATA_DIR")
    legacy_tasks_dir: Path = Field(default=PROJECT_ROOT / "tasks", alias="LEGACY_TASKS_DIR")

    optional_redis_url: str | None = Field(default=None, alias="OPTIONAL_REDIS_URL")


settings = Settings()
settings.data_dir.mkdir(parents=True, exist_ok=True)
