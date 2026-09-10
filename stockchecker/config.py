"""Runtime configuration, loaded from environment variables and an optional ``.env`` file."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    db_path: Path = Path("data/stockchecker.db")
    discord_token: str | None = None
    request_delay_s: float = 1.0
    max_workers: int = 4
    universe_file: Path = Path("data/tickers.txt")
    log_level: str = "INFO"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


def configure_logging(level: str | None = None) -> None:
    """Configure root logging once. Uses rich's handler when available for readable output."""
    resolved = (level or get_settings().log_level).upper()
    handlers: list[logging.Handler] = []
    try:
        from rich.logging import RichHandler

        handlers.append(RichHandler(rich_tracebacks=False, show_path=False))
    except ImportError:  # pragma: no cover - rich is a hard dependency, but stay defensive
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=resolved, format="%(message)s", handlers=handlers, force=True)
    # Third-party libraries are noisy at INFO/DEBUG.
    for noisy in ("urllib3", "peewee", "discord"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    # yfinance logs every unknown ticker at ERROR; we surface those ourselves.
    logging.getLogger("yfinance").setLevel(logging.CRITICAL)
