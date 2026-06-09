"""Premium layer: access/expiry, referrals, certificates, career, payments."""
from __future__ import annotations

from datetime import date, timedelta

from database import models
from lessons import get_course
from services import (
    access_service,
    career_service,
    certificate_service,
    payment_service,
    pricing,
    progress_service,
    referral_service,
    user_service,
)

BEGINNER = progress_service.BEGINNER


async def _complete_beginner(uid: int) -> None:
    """Push the Beginner pointer past the last lesson (course finished)."""
    await models.set_current_lesson(uid, get_course(BEGINNER).total + 1)


# ── Access / tiers / expiry ──────────────────────────────────────────────────

async def test_access_grant_expiry_and_revoke():
    uid = 940_001
    await user_service.register_user(uid, "acc")
    assert access_service.tier(await models.get_user(uid)) == "FREE"

    await access_service.grant(uid, 30)
    assert access_service.is_pro(await models.get_user(uid))

    await access_service.grant(uid, None)  # lifetime
    u = await models.get_user(uid)
    assert access_service.is_pro(u) and access_service.expiry(u) is None

    await models.set_pro_access(uid, True, "2000-01-01")  # expired
    assert not access_service.is_pro(await models.get_user(uid))

    await access_service.grant(uid, 10)
    await access_service.revoke(uid)
    assert not access_service.is_pro(await models.get_user(uid))


async def test_access_stacks_days():
    uid = 940_002
    await user_service.register_user(uid, "acc2")
    await access_service.grant(uid, 10)
    until2 = await access_service.grant(uid, 10)  # extends, not resets
    assert until2 == (date.today() + timedelta(days=20)).isoformat()


# ── Referrals (viral loop) ───────────────────────────────────────────────────

async def test_referral_attribution_and_reward_once():
    referrer = 941_001
    friend = 941_002
    await user_service.register_user(referrer, "ref")
    await user_service.register_user(friend, "friend")

    payload = referral_service.make_payload(referrer)
    assert await referral_service.attribute(friend, payload) is True
    assert (await models.get_user(friend)).ref_by == referrer
    assert access_service.is_pro(await models.get_user(friend))  # welcome trial granted

    # Attribution is one-time.
    assert await referral_service.attribute(friend, referral_service.make_payload(999)) is False

    # Friend pays → referrer rewarded exactly once.
    assert await referral_service.reward_for_purchase(friend) == referrer
    assert access_service.is_pro(await models.get_user(referrer))
    assert await referral_service.reward_for_purchase(friend) is None  # no double reward

    invited, converted = await referral_service.stats(referrer)
    assert invited >= 1 and converted >= 1


async def test_referral_rejects_self_and_unknown():
    uid = 941_010
    await user_service.register_user(uid, "solo")
    assert await referral_service.attribute(uid, referral_service.make_payload(uid)) is False
    assert await referral_service.attribute(uid, "ref_88888888") is False
    assert await referral_service.attribute(uid, None) is False


# ── Certificates ─────────────────────────────────────────────────────────────

async def test_certificate_issued_only_on_completion():
    uid = 942_001
    await user_service.register_user(uid, "student")
    cert, newly = await certificate_service.issue(uid, BEGINNER)
    assert cert is None and not newly  # not finished yet

    await _complete_beginner(uid)
    cert, newly = await certificate_service.issue(uid, BEGINNER)
    assert cert is not None and newly
    assert certificate_service.verify(cert.code, uid, BEGINNER)
    assert not certificate_service.verify(cert.code, uid, "web_python")

    # Re-issue is idempotent (same code, not "newly").
    again, newly2 = await certificate_service.issue(uid, BEGINNER)
    assert again.code == cert.code and not newly2


# ── Career Path ──────────────────────────────────────────────────────────────

async def test_career_report_shape_and_growth():
    uid = 943_001
    await user_service.register_user(uid, "career")
    before = await career_service.report(uid)
    assert before is not None
    assert 0 <= before.readiness <= 100
    assert len(before.milestones) == 5  # 4 courses + projects
    assert before.next_step

    await _complete_beginner(uid)
    after = await career_service.report(uid)
    assert after.readiness >= before.readiness
    assert any(m.done for m in after.milestones)  # a milestone is now complete


# ── Pricing & payment fulfilment ─────────────────────────────────────────────

def test_pricing_catalog():
    assert pricing.PRODUCTS
    assert pricing.get("pro_month") is not None
    assert pricing.get("nonsense") is None


async def test_payment_fulfilment_grants_access():
    uid = 944_001
    await user_service.register_user(uid, "payer")
    product = await payment_service.fulfill(uid, "pro_month", "charge_test_1")
    assert product is not None and product.id == "pro_month"
    assert access_service.is_pro(await models.get_user(uid))
    assert await payment_service.fulfill(uid, "bogus", "x") is None
