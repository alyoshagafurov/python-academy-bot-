"""Admin panel via Telegram commands (gated by config.admin_ids).

Commands:
    /admin               — platform stats (users, retention, XP, lessons)
    /grant_pro <id>      — grant PRO to a user
    /revoke_pro <id>     — revoke PRO
"""
from __future__ import annotations

from aiogram import Router
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from services import admin_service
from utils import texts

router = Router(name="admin")


def _overview_text(ov) -> str:
    return (
        "🛠 <b>Admin · Python Academy</b>\n\n"
        f"👥 Пользователей: <b>{ov.total_users}</b>\n"
        f"🟢 Активны сегодня: <b>{ov.active_today}</b>\n"
        f"📆 Активны за 7 дней: <b>{ov.active_7d}</b>\n"
        f"📈 Retention (7d): <b>{ov.retention_pct}%</b>\n"
        f"💎 PRO-пользователей: <b>{ov.pro_users}</b>\n\n"
        f"⚡ Всего XP: <b>{ov.total_xp}</b>\n"
        f"📚 Уроков завершено: <b>{ov.lessons_completed}</b>\n"
        f"📅 Daily сегодня: <b>{ov.daily_today}</b>\n"
        f"🎯 Ответов: <b>{ov.attempts}</b> · точность <b>{ov.accuracy_pct}%</b>\n\n"
        "<code>/grant_pro &lt;id&gt;</code> · <code>/revoke_pro &lt;id&gt;</code>"
    )


@router.message(Command("admin"))
async def cmd_admin(message: Message, state: FSMContext) -> None:
    if not admin_service.is_admin(message.from_user.id):
        return  # stay invisible to non-admins
    await state.clear()
    overview = await admin_service.overview()
    analytics = await admin_service.analytics()
    await message.answer(f"{_overview_text(overview)}\n\n{texts.admin_headline(analytics)}")


@router.message(Command("analytics"))
async def cmd_analytics(message: Message, state: FSMContext) -> None:
    if not admin_service.is_admin(message.from_user.id):
        return  # stay invisible to non-admins
    await state.clear()
    analytics = await admin_service.analytics()
    await message.answer(texts.admin_analytics(analytics))


@router.message(Command("grant_pro"))
async def cmd_grant_pro(message: Message, command: CommandObject) -> None:
    if not admin_service.is_admin(message.from_user.id):
        return
    target = (command.args or "").strip()
    if not target.lstrip("-").isdigit():
        await message.answer("Использование: <code>/grant_pro &lt;user_id&gt;</code>")
        return
    ok = await admin_service.grant_pro(int(target))
    await message.answer(f"💎 PRO выдан пользователю {target}" if ok else f"Пользователь {target} не найден.")


@router.message(Command("revoke_pro"))
async def cmd_revoke_pro(message: Message, command: CommandObject) -> None:
    if not admin_service.is_admin(message.from_user.id):
        return
    target = (command.args or "").strip()
    if not target.lstrip("-").isdigit():
        await message.answer("Использование: <code>/revoke_pro &lt;user_id&gt;</code>")
        return
    ok = await admin_service.revoke_pro(int(target))
    await message.answer(f"PRO снят у пользователя {target}" if ok else f"Пользователь {target} не найден.")
