"""Per-user throttling middleware (anti-abuse / anti double-tap).

Deterministic, in-memory, O(1). Drops bursts faster than ``min_interval``
without annoying normal users. Callback spinners are always stopped so the
UI never appears frozen.
"""
from __future__ import annotations

import logging
import time
from contextlib import suppress
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, TelegramObject

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    """Allow at most one handled event per ``min_interval`` seconds per user."""

    def __init__(self, min_interval: float = 0.35, prune_after: int = 10_000) -> None:
        self.min_interval = min_interval
        self.prune_after = prune_after
        self._last_seen: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        if user is not None:
            now = time.monotonic()
            last = self._last_seen.get(user.id, 0.0)
            if now - last < self.min_interval:
                # Too fast → drop, but never leave a callback spinner hanging.
                if isinstance(event, CallbackQuery):
                    with suppress(Exception):
                        await event.answer()
                return None
            self._last_seen[user.id] = now
            if len(self._last_seen) > self.prune_after:
                self._prune(now)
        return await handler(event, data)

    def _prune(self, now: float) -> None:
        """Drop stale entries so the map can't grow unbounded."""
        cutoff = now - 60.0
        self._last_seen = {uid: ts for uid, ts in self._last_seen.items() if ts > cutoff}
