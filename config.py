"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

# Load variables from the local .env file (if present).
load_dotenv(BASE_DIR / ".env")

# Values that mean "the token hasn't been filled in yet".
_PLACEHOLDER_TOKENS = {"", "PASTE_NEW_TOKEN_HERE", "your-telegram-bot-token-here"}


def _parse_ids(raw: str | None) -> frozenset[int]:
    """Parse a comma/semicolon separated list of Telegram IDs."""
    ids: set[int] = set()
    for part in (raw or "").replace(";", ",").split(","):
        part = part.strip()
        if part.lstrip("-").isdigit():
            ids.add(int(part))
    return frozenset(ids)


@dataclass(frozen=True)
class Config:
    """Strongly-typed application settings."""

    bot_token: str
    db_path: Path
    admin_ids: frozenset[int]
    pro_ids: frozenset[int]
    payments_enabled: bool   # turn on the Telegram Stars checkout flow


def load_config() -> Config:
    """Read and validate configuration. Fails fast if the token is missing."""
    token = os.getenv("BOT_TOKEN", "").strip()
    if token in _PLACEHOLDER_TOKENS:
        raise RuntimeError(
            "BOT_TOKEN не задан. Открой файл .env и вставь токен от @BotFather:\n"
            "    BOT_TOKEN=123456789:ABC...\n"
            "Шаблон переменных — в .env.example."
        )

    db_path = (BASE_DIR / os.getenv("DB_PATH", "academy.db")).resolve()
    payments_enabled = os.getenv("PAYMENTS_ENABLED", "").strip().lower() in {"1", "true", "yes", "on"}
    return Config(
        bot_token=token,
        db_path=db_path,
        admin_ids=_parse_ids(os.getenv("ADMIN_IDS")),
        pro_ids=_parse_ids(os.getenv("PRO_IDS")),
        payments_enabled=payments_enabled,
    )


# Singleton config, imported across the project.
config = load_config()
