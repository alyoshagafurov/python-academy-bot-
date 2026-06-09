"""Context-aware reminder nudges: booster selection + composed message."""
from __future__ import annotations

from database import models
from services import adaptive_service, level_service, nudge_service, user_service


# ── Pure booster selection ──────────────────────────────────────────────────

def test_booster_prefers_xp_when_close_to_level():
    level = level_service.level_info(70)   # next level at 100 → 30 XP away
    assert level.to_next <= 60
    msg = nudge_service.booster_from_signals(level, near_topic="Списки")
    assert "XP" in msg and "до уровня" in msg


def test_booster_uses_topic_when_far_from_level():
    level = level_service.level_info(0)     # 100 XP away → too far for XP nudge
    msg = nudge_service.booster_from_signals(level, near_topic="Словари")
    assert "Словари" in msg


def test_booster_generic_when_no_signal():
    level = level_service.level_info(0)
    msg = nudge_service.booster_from_signals(level, near_topic=None)
    assert msg and "XP" not in msg


def test_streak_line_includes_day_count():
    assert "5-дневный" in nudge_service.streak_line(5)


# ── Composed message (integration) ──────────────────────────────────────────

async def test_compose_mentions_streak_and_xp_when_near_level():
    uid = 830_001
    await user_service.register_user(uid, "almost")
    await models.add_xp(uid, 70)                          # 30 XP to level 2
    await models.set_streak(uid, 4, 4, "2026-01-01")
    msg = await nudge_service.compose(uid)
    assert "4-дневный" in msg
    assert "XP" in msg


async def test_compose_surfaces_near_mastery_topic():
    uid = 830_002
    await user_service.register_user(uid, "nearmaster")   # xp 0 → XP nudge won't trigger
    await models.set_streak(uid, 3, 3, "2026-01-01")
    # Two correct answers push 'lists' confidence into the near-mastery band.
    await adaptive_service.record_outcome(uid, "lists", correct=True)
    await adaptive_service.record_outcome(uid, "lists", correct=True)
    msg = await nudge_service.compose(uid)
    assert "Списки" in msg


async def test_compose_falls_back_for_unknown_user():
    msg = await nudge_service.compose(999_999_999)
    assert isinstance(msg, str) and msg
