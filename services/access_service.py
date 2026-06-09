"""Access tiers and PRO entitlement (with expiry).

The single source of truth for "can this user use paid features". PRO can be:
  • from the config allow-list (config.pro_ids) — always on,
  • a lifetime flag (is_pro=1, pro_until=NULL),
  • or time-limited (is_pro=1, pro_until=ISO date) — auto-expires.
"""
from __future__ import annotations

from datetime import date, timedelta

from config import config
from database import models
from database.models import User

FREE = "FREE"
PRO = "PRO"


def is_pro(user: User | None) -> bool:
    if user is None:
        return False
    if user.user_id in config.pro_ids:
        return True
    if not user.is_pro:
        return False
    if user.pro_until is None:
        return True  # lifetime
    return user.pro_until >= date.today().isoformat()


def tier(user: User | None) -> str:
    return PRO if is_pro(user) else FREE


def expiry(user: User | None) -> str | None:
    """ISO expiry date for a time-limited PRO, or None (lifetime / not pro)."""
    if user is None or not user.is_pro or user.user_id in config.pro_ids:
        return None
    return user.pro_until


async def grant(user_id: int, days: int | None) -> str | None:
    """Grant or extend PRO. ``days=None`` ⇒ lifetime. Time grants extend from the
    later of today / current expiry. Returns the new expiry (None for lifetime)."""
    user = await models.get_user(user_id)
    if days is None:
        await models.set_pro_access(user_id, True, None)
        return None
    # Already lifetime → keep it, don't downgrade to a fixed date.
    if user and user.is_pro and user.pro_until is None:
        return None
    base = date.today()
    if user and user.is_pro and user.pro_until:
        current = date.fromisoformat(user.pro_until)
        if current > base:
            base = current
    until = (base + timedelta(days=days)).isoformat()
    await models.set_pro_access(user_id, True, until)
    return until


async def revoke(user_id: int) -> None:
    await models.set_pro_access(user_id, False, None)
