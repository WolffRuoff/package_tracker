"""Runtime settings for the scraper, sourced from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings

from .const import DB_PATH, DEFAULT_PORT


class Settings(BaseSettings):
    """Environment-driven configuration.

    Fields are populated (case-insensitively) from the matching environment
    variables: ``PORT`` and ``DB_PATH``.
    """

    port: int = DEFAULT_PORT
    db_path: str = DB_PATH


settings = Settings()
