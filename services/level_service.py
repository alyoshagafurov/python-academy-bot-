"""XP → level math and presentation helpers (pure functions)."""
from __future__ import annotations

from dataclasses import dataclass

from utils.gamification import progress_bar

# Cumulative XP required to *reach* each level (index 0 → level 1).
_THRESHOLDS: list[int] = [
    0, 100, 250, 500, 850, 1300, 1900, 2600,
    3400, 4300, 5300, 6400, 7600, 8900, 10300,
]
# XP added per level once the table above is exhausted.
_STEP_BEYOND = 1500

_TITLES: dict[int, str] = {
    1: "🌱 Beginner",
    2: "📘 Learner",
    3: "🧠 Python Explorer",
    4: "⚙️ Code Builder",
    5: "🚀 Pythonista",
    6: "🥷 Code Ninja",
}
_TITLE_MAX = "🏆 Python Master"


@dataclass(frozen=True)
class LevelInfo:
    level: int
    title: str
    xp: int
    floor: int          # XP at the start of this level
    next_threshold: int  # XP needed for the next level
    into_level: int     # XP earned inside the current level
    span: int           # XP width of the current level
    to_next: int        # XP remaining until the next level
    percent: int        # 0..100 progress inside the level
    bar: str            # rendered progress bar


def _threshold(level: int) -> int:
    """Cumulative XP needed to reach `level` (1-based), extrapolating past the table."""
    if level <= len(_THRESHOLDS):
        return _THRESHOLDS[level - 1]
    extra = level - len(_THRESHOLDS)
    return _THRESHOLDS[-1] + _STEP_BEYOND * extra


def level_title(level: int) -> str:
    return _TITLES.get(level, _TITLE_MAX)


def level_info(xp: int) -> LevelInfo:
    """Resolve a full level breakdown from a raw XP amount."""
    xp = max(0, xp)

    level = 1
    while xp >= _threshold(level + 1):
        level += 1

    floor = _threshold(level)
    next_threshold = _threshold(level + 1)
    span = next_threshold - floor
    into_level = xp - floor
    to_next = next_threshold - xp
    percent = int(into_level / span * 100) if span else 100

    return LevelInfo(
        level=level,
        title=level_title(level),
        xp=xp,
        floor=floor,
        next_threshold=next_threshold,
        into_level=into_level,
        span=span,
        to_next=to_next,
        percent=percent,
        bar=progress_bar(into_level, span, length=10),
    )
