"""Code Practice: the user writes real Python and sends it as a message.

Submissions are validated structurally via AST (services.code_check) — nothing
is ever executed, so it's safe.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import inline
from keyboards.callbacks import CodeCB, MenuCB
from services import code_service, feature_service, user_service
from states import CodeStates
from utils import texts
from utils.telegram import safe_edit, typing

router = Router(name="code")


@router.callback_query(MenuCB.filter(F.action == "code"))
async def open_code(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = await user_service.get_user(query.from_user.id)
    await safe_edit(query.message, texts.code_intro(), inline.code_categories(feature_service.is_pro(user)))
    await query.answer()


@router.callback_query(CodeCB.filter(F.action == "task"))
async def serve_task(query: CallbackQuery, callback_data: CodeCB, state: FSMContext) -> None:
    topic = callback_data.topic
    user = await user_service.get_user(query.from_user.id)

    if not feature_service.can_code_topic(user, topic):
        await safe_edit(
            query.message,
            texts.upsell("💻 Code Practice по темам <b>Loops</b> и <b>Functions</b> — в PRO."),
            inline.upsell(),
        )
        await query.answer(texts.PRO_LOCKED_ALERT, show_alert=True)
        return

    task = code_service.random_task(topic)
    if task is None:
        await query.answer("Скоро добавим задачи по этой теме!", show_alert=True)
        return

    await state.set_state(CodeStates.waiting)
    await state.update_data(task_id=task.id, topic=topic)
    await typing(query.bot, query.message.chat.id, 0.3)
    await safe_edit(query.message, texts.code_task_card(task), inline.code_task(topic))
    await query.answer()


@router.message(CodeStates.waiting, F.text & ~F.text.startswith("/"))
async def submit_code(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    task_id, topic = data.get("task_id"), data.get("topic", "")
    if not task_id:
        await state.clear()
        return

    # FREE daily quota (wrong attempts are free — only solves count).
    allowed, _used, limit = await feature_service.practice_quota(message.from_user.id)
    if not allowed:
        await state.clear()
        await message.answer(texts.practice_limit_reached(limit), reply_markup=inline.upsell())
        return

    await typing(message.bot, message.chat.id, 0.5)
    result = await code_service.submit(message.from_user.id, task_id, message.text or "")
    if result is None:
        await state.clear()
        await message.answer("Задача потерялась 🤔 Открой Code Practice заново.", reply_markup=inline.back_to_menu())
        return

    if result.passed:
        await feature_service.consume_practice(message.from_user.id)
        await state.clear()
        await message.answer(texts.code_pass(result), reply_markup=inline.code_task(topic))
    else:
        # Stay in the waiting state so the user can simply resend corrected code.
        await message.answer(texts.code_fail(result), reply_markup=inline.code_task(topic))


@router.message(Command("code"))
async def cmd_code(message: Message, state: FSMContext) -> None:
    await state.clear()
    tg = message.from_user
    user = await user_service.register_user(tg.id, tg.username or tg.full_name)
    await message.answer(texts.code_intro(), reply_markup=inline.code_categories(feature_service.is_pro(user)))
