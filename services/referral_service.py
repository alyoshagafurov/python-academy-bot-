"""Referrals — the word-of-mouth engine.

Each user has a personal deep link (``t.me/bot?start=ref_<id>``). When a new
user joins through it, the referrer is attributed once and the friend gets a
welcome trial. When that friend later pays, the referrer is rewarded once with
bonus PRO days. Everything is idempotent (no farming).
"""
from __future__ import annotations

from datetime import datetime, timezone

from database import models
from services import access_service, runtime
from services.pricing import REFERRAL_REWARD_DAYS, REFERRAL_WELCOME_DAYS

_PREFIX = "ref_"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def make_payload(user_id: int) -> str:
    return f"{_PREFIX}{user_id}"


def parse_payload(payload: str | None) -> int | None:
    if not payload or not payload.startswith(_PREFIX):
        return None
    raw = payload[len(_PREFIX):]
    return int(raw) if raw.isdigit() else None


def invite_link(user_id: int) -> str:
    """Personal deep link, or '' if the bot username isn't known yet."""
    username = runtime.BOT_USERNAME
    return f"https://t.me/{username}?start={make_payload(user_id)}" if username else ""


async def attribute(new_user_id: int, payload: str | None) -> bool:
    """Attribute a referrer from a /start payload (once). Grants the new user a
    welcome trial. No-op for self-referral or unknown referrer."""
    referrer_id = parse_payload(payload)
    if referrer_id is None or referrer_id == new_user_id:
        return False
    if await models.get_user(referrer_id) is None:
        return False
    if not await models.set_ref_by(new_user_id, referrer_id):
        return False  # already attributed earlier
    if REFERRAL_WELCOME_DAYS:
        await access_service.grant(new_user_id, REFERRAL_WELCOME_DAYS)
    return True


async def reward_for_purchase(referee_id: int) -> int | None:
    """Reward the referrer once when a referred friend pays. Returns referrer id."""
    user = await models.get_user(referee_id)
    if user is None or not user.ref_by:
        return None
    if await models.add_referral_reward(referee_id, user.ref_by, _now()):
        await access_service.grant(user.ref_by, REFERRAL_REWARD_DAYS)
        return user.ref_by
    return None


async def stats(user_id: int) -> tuple[int, int]:
    """(invited, converted) friends for this user."""
    return await models.referral_stats(user_id)
