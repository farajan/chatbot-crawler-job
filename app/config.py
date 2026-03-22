"""
Centralized application configuration.

All values come from environment variables (K8s ConfigMap, Secret, Job spec).
Defaults are safe for local development.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parent.parent / ".env.localhost"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE if _ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    crawl_job_id: str
    max_depth: int = 5
    max_pages: int = 2000

    db_host: str = "127.0.0.1"
    db_port: int = 5432
    db_name: str = "chatbot"
    db_user: str = "chatbot"
    db_password: str = "postgres"
    db_pool_min_size: int = 1
    db_pool_max_size: int = 20
    db_timeout_seconds: float = 10


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
