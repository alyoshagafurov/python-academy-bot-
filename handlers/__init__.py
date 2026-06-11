"""Handler routers, assembled into one root router for the dispatcher.

Theory-first hub + interactive practice (write & run real Python) + gamification
(achievements, weekly leaderboard) + the premium program layer (Career Path,
projects, certificates, referrals, Stars checkout). The remaining dormant
modules (practice, daily, coach) stay on disk but are not registered.
"""
from __future__ import annotations

from aiogram import Router

from . import (
    achievements,
    admin,
    code,
    common,
    courses,
    discover,
    leaderboard,
    lessons,
    modes,
    payments,
    premium,
    profile,
    projects,
    sandbox,
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
    router.include_router(code.router)      # Code Practice (AST-checked, safe)
    router.include_router(sandbox.router)   # Code Runner (real sandboxed execution)
    router.include_router(achievements.router)
    router.include_router(leaderboard.router)
    router.include_router(premium.router)   # career / invite / certificate
    router.include_router(projects.router)  # paid portfolio projects (gated inside)
    router.include_router(payments.router)  # Stars offer + checkout
    router.include_router(profile.router)
    router.include_router(admin.router)
    router.include_router(common.router)    # fallback — keep last
    return router
