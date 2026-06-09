"""Products & pricing for the paid program (Telegram Stars).

Prices are in Telegram Stars (XTR). Stars need no merchant account, work
globally and are the simplest way to charge inside Telegram. ₽-labels are for
display only. Tune freely — nothing else depends on the exact numbers.
"""
from __future__ import annotations

from dataclasses import dataclass

# A friend's purchase grants the referrer this many bonus PRO days.
REFERRAL_REWARD_DAYS = 30
# A newly-referred user starts with this many trial PRO days (sweetens invites).
REFERRAL_WELCOME_DAYS = 7


@dataclass(frozen=True)
class Product:
    id: str
    title: str
    days: int | None       # None ⇒ lifetime access
    stars: int             # price in Telegram Stars (XTR)
    price_label: str       # human label for screens
    blurb: str


PRODUCTS: tuple[Product, ...] = (
    Product("pro_month", "PRO · 1 месяц", 30, 399, "≈ 799 ₽",
            "Полный доступ на 30 дней: проекты, проверка, сертификат."),
    Product("program", "Полная программа · навсегда", None, 2490, "≈ 4 990 ₽",
            "Все курсы, проекты, проверка кода, сертификаты и будущие обновления — навсегда."),
)

_BY_ID = {p.id: p for p in PRODUCTS}


def get(product_id: str) -> Product | None:
    return _BY_ID.get(product_id)
