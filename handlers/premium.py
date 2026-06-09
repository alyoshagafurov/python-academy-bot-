"""Premium screens: Career Path, referral invite, completion certificate."""
from __future__ import annotations

from urllib.parse import quote

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import inline
from keyboards.callbacks import MenuCB
from lessons import get_course
from services import (
    access_service,
    career_service,
    certificate_service,
    progress_service,
    referral_service,
    runtime,
    user_service,
)
from services.pricing import REFERRAL_REWARD_DAYS, REFERRAL_WELCOME_DAYS
from utils import texts
from utils.telegram import safe_edit, typing

router = Router(name="premium")


# ──────────────────────────────── Career Path ─────────────────────────────

@router.callback_query(MenuCB.filter(F.action == "career"))
async def open_career(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    report = await career_service.report(query.from_user.id)
    if report is None:
        await query.answer()
        return
    user = await user_service.get_user(query.from_user.id)
    await typing(query.bot, query.message.chat.id, 0.4)
    await safe_edit(query.message, texts.career(report), inline.career(access_service.is_pro(user)))
    await query.answer()


@router.message(Command("career"))
async def cmd_career(message: Message, state: FSMContext) -> None:
    await state.clear()
    tg = message.from_user
    await user_service.register_user(tg.id, tg.username or tg.full_name)
    report = await career_service.report(tg.id)
    if report is not None:
        user = await user_service.get_user(tg.id)
        await message.answer(texts.career(report), reply_markup=inline.career(access_service.is_pro(user)))


# ───────────────────────────────── Invite ─────────────────────────────────

async def _invite_text(user_id: int) -> str:
    link = referral_service.invite_link(user_id)
    invited, converted = await referral_service.stats(user_id)
    return texts.invite(link, invited, converted, REFERRAL_REWARD_DAYS, REFERRAL_WELCOME_DAYS)


@router.callback_query(MenuCB.filter(F.action == "invite"))
async def open_invite(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    tg = query.from_user
    await user_service.register_user(tg.id, tg.username or tg.full_name)
    await safe_edit(query.message, await _invite_text(tg.id), inline.invite())
    await query.answer()


@router.message(Command("invite"))
async def cmd_invite(message: Message, state: FSMContext) -> None:
    await state.clear()
    tg = message.from_user
    await user_service.register_user(tg.id, tg.username or tg.full_name)
    await message.answer(await _invite_text(tg.id), reply_markup=inline.invite())


# ─────────────────────────────── Certificate ──────────────────────────────

def _share_url(cert) -> str:
    base = f"https://t.me/{runtime.BOT_USERNAME}" if runtime.BOT_USERNAME else "https://t.me"
    return f"https://t.me/share/url?url={quote(base)}&text={quote(texts.certificate_share(cert))}"


@router.callback_query(MenuCB.filter(F.action == "certificate"))
async def open_certificate(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = await user_service.get_user(query.from_user.id)
    if user is None:
        await query.answer()
        return
    course_id = progress_service.active_course_id(user)
    title = get_course(course_id).title
    completed = await certificate_service.is_completed(user, course_id)
    is_pro = access_service.is_pro(user)

    if completed and is_pro:
        cert, newly = await certificate_service.issue(query.from_user.id, course_id)
        await safe_edit(query.message, texts.certificate_card(cert, newly),
                        inline.certificate(share_url=_share_url(cert)))
    elif completed and not is_pro:
        await safe_edit(query.message, texts.certificate_locked(title, True),
                        inline.certificate(show_pro=True))
    else:
        await safe_edit(query.message, texts.certificate_locked(title, False), inline.certificate())
    await query.answer()
