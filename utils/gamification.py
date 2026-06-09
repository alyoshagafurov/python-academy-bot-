"""Pure helpers for XP ranks and progress visualization."""
from __future__ import annotations

# (min_xp, title) thresholds, ascending.
RANKS: list[tuple[int, str]] = [
    (0, "🌱 Семечко"),
    (20, "🌿 Росток"),
    (40, "🌳 Знаток"),
    (60, "🏆 Мастер Python"),
]

MODE_NAMES: dict[str, str] = {
    "kid": "🟢 Детский",
    "beginner": "🔵 Новичок",
    "student": "🟣 Студент",
}


def get_rank(xp: int) -> str:
    """Return the rank title for a given amount of XP."""
    title = RANKS[0][1]
    for threshold, name in RANKS:
        if xp >= threshold:
            title = name
    return title


def progress_bar(done: int, total: int, length: int = 10) -> str:
    """Render a unicode progress bar, e.g. ▰▰▰▱▱▱▱▱▱▱."""
    if total <= 0:
        return "▱" * length
    done = max(0, min(done, total))
    filled = round(length * done / total)
    return "▰" * filled + "▱" * (length - filled)


def mode_title(mode: str | None) -> str:
    """Human-friendly mode label."""
    if not mode:
        return "не выбран"
    return MODE_NAMES.get(mode, mode)
