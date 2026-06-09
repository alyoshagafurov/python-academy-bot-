"""Daily Challenge content.

One challenge per calendar day, chosen deterministically so every user sees
the same task that rotates each day.
"""
from __future__ import annotations

from datetime import date

from lessons.schema import Quiz

DAILY: tuple[Quiz, ...] = (
    Quiz("Что выведет код?", ("10", "52", "7", "Ошибка"), 0,
         "5 * 2 = 10.", code="x = 5\nprint(x * 2)", topic="variables"),
    Quiz("Что выведет код?", ("6", "5", "python", "Ошибка"), 0,
         "В слове python 6 букв, len считает их.", code="print(len('python'))", topic="variables"),
    Quiz("Сколько раз напечатается «hi»?", ("2 раза", "1 раз", "3 раза", "Ошибка"), 0,
         "range(2) → два повтора.", code="for i in range(2):\n    print('hi')", topic="loops"),
    Quiz("Что выведет код?", ("2", "1", "3", "Ошибка"), 0,
         "Индексация с 0: a[1] — второй элемент = 2.", code="a = [1, 2, 3]\nprint(a[1])", topic="lists"),
    Quiz("Что выведет код?", ("нечёт", "чёт", "7", "Ошибка"), 0,
         "7 на 2 без остатка не делится → нечёт.",
         code="x = 7\nif x % 2 == 0:\n    print('чёт')\nelse:\n    print('нечёт')", topic="conditions"),
    Quiz("Что выведет код?", ("True", "False", "3", "Ошибка"), 0,
         "3 больше 2 — это правда → True.", code="print(3 > 2)", topic="conditions"),
    Quiz("Что выведет код?", ("10", "9", "x + 1", "Ошибка"), 0,
         "f(9) = 9 + 1 = 10.", code="def f(x):\n    return x + 1\nprint(f(9))", topic="functions"),
    Quiz("Что выведет код?", ("ababab", "abababab", "ab3", "Ошибка"), 0,
         "Строка * число повторяет её: 'ab' * 3 = 'ababab'.", code="print('ab' * 3)", topic="variables"),
)

DAILY_BASE_XP = 15


def today_index(today: date | None = None) -> int:
    """Deterministic index for today's challenge."""
    today = today or date.today()
    return today.toordinal() % len(DAILY)


def get_today(today: date | None = None) -> Quiz:
    return DAILY[today_index(today)]
