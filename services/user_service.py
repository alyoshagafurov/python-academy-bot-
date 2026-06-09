"""User-centric business logic: registration, mode selection, progress."""
from __future__ import annotations

from database import models
from database.models import User


async def register_user(user_id: int, username: str | None) -> User:
    """Register the user on first contact, or refresh their username."""
    existing = await models.get_user(user_id)
    if existing is None:
        return await models.create_user(user_id, username)

    if existing.username != username:
        await models.update_username(user_id, username)
        existing.username = username
    return existing


async def get_user(user_id: int) -> User | None:
    """Return the user's current state, or None if unregistered."""
    return await models.get_user(user_id)


async def select_mode(user_id: int, mode: str) -> None:
    """Store the learning mode chosen by the user."""
    await models.set_mode(user_id, mode)
