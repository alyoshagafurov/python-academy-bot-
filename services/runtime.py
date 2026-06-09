"""Tiny runtime holder for values discovered at startup (e.g. bot username).

Kept separate so pure services can read it without importing the bot/dispatcher.
"""
from __future__ import annotations

# Set once in bot.py after get_me(); used to build referral deep links.
BOT_USERNAME: str = ""


def set_bot_username(username: str) -> None:
    global BOT_USERNAME
    BOT_USERNAME = username or ""
