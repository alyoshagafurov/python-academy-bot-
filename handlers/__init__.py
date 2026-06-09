"""Handler routers, assembled into one root router for the dispatcher.

Theory-first hub (free) + premium program layer (paid): theory, discovery,
Career Path, projects, certificates, referrals and Stars checkout. The remaining
interactive modules (code, sandbox, practice, daily, coach, achievements,
leaderboard) stay on disk but are intentionally NOT registered.
"""
from __future__ import annotations

from aiogram import Router

from . import (
    admin,
    common,
    courses,
    discover,
    lessons,
    modes,
    payments,
    premium,
    profile,
    projects,
    snippets,
    start,
)


def get_main_router() -> Router:
    """Combine the active routers. `common` is last (catch-all)."""
    router = Router(name="main")
    router.include_router(start.router)
    router.include_router(modes.router)
    router.include_router(courses.router)
    router.include_router(lessons.router)
    router.include_router(snippets.router)  # Minecraft code library
    router.include_router(discover.router)
    router.include_router(premium.router)   # career / invite / certificate
    router.include_router(projects.router)  # paid portfolio projects (gated inside)
    router.include_router(payments.router)  # Stars offer + checkout
    router.include_router(profile.router)
    router.include_router(admin.router)
    router.include_router(common.router)    # fallback — keep last
    return router
