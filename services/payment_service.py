"""Payment fulfilment (Telegram Stars).

Stars (currency ``XTR``) need no merchant account or provider token, so this
works on any live bot. Fulfilment is idempotent-friendly: it grants access,
records the purchase for audit, and triggers the referral reward for the buyer's
inviter (rewarded at most once per friend).
"""
from __future__ import annotations

from datetime import datetime, timezone

from config import config
from database import models
from services import access_service, pricing, referral_service
from services.pricing import Product


def enabled() -> bool:
    """Whether the live Stars checkout is turned on (PAYMENTS_ENABLED=1)."""
    return config.payments_enabled


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


async def fulfill(user_id: int, product_id: str, charge_id: str) -> Product | None:
    """Grant access for a paid product, record it, and reward the referrer."""
    product = pricing.get(product_id)
    if product is None:
        return None
    await access_service.grant(user_id, product.days)
    await models.record_purchase(user_id, product.id, product.stars, charge_id, _now())
    await referral_service.reward_for_purchase(user_id)
    return product
