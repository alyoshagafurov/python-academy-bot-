"""Feature flags & soft monetization (FREE vs PRO).

No payments yet — PRO status comes from a per-user flag (admin-grantable) or
a config allow-list. The gates below are real and enforced; payment wiring
(Telegram Stars / Payments) is the only missing piece.
"""
from __future__ import annotations

from datetime import date

from config import config
from database import models
from database.models import User

FREE_PRACTICE_LIMIT = 20  # free quiz/code answers per day

# Marketing copy for the upsell screen (label, blurb).
PRO_PERKS: tuple[tuple[str, str], ...] = (
    ("🔴 Hard mode", "сложные задачи во всех темах"),
    ("💻 Code: Loops & Functions", "продвинутая практика с реальным кодом"),
    ("♾️ Безлимит практики", "без дневного лимита"),
    ("🟣 Student mode", "углублённый трек (скоро)"),
    ("🤖 AI-разборы ошибок", "персональные объяснения (скоро)"),
)

# Code-practice topics available on the free tier.
_FREE_CODE_TOPICS = {"variables", "lists"}


def is_pro(user: User | None) -> bool:
    # Single source of truth lives in access_service (respects PRO expiry).
    from services import access_service
    return access_service.is_pro(user)


def can_hard_mode(user: User | None) -> bool:
    return is_pro(user)


def can_code_topic(user: User | None, topic: str) -> bool:
    return topic in _FREE_CODE_TOPICS or is_pro(user)


async def practice_quota(user_id: int) -> tuple[bool, int, int]:
    """Return (allowed, used_today, limit). PRO users are unlimited (limit 0)."""
    user = await models.get_user(user_id)
    if is_pro(user):
        return True, 0, 0
    today = date.today().isoformat()
    used = user.practice_count if user and user.practice_date == today else 0
    return used < FREE_PRACTICE_LIMIT, used, FREE_PRACTICE_LIMIT


async def consume_practice(user_id: int) -> None:
    """Count one practice answer toward today's free quota."""
    await models.bump_practice_count(user_id, date.today().isoformat())
