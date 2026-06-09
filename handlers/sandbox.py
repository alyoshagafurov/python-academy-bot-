"""Code Runner (real sandboxed execution) + Debug mode.

Flow: pick task → write a function → it runs against hidden tests → explainable
feedback → retry (XP bonus for first-pass). Debug mode explains broken code.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import models
from keyboards import inline
from keyboards.callbacks import MenuCB, SandboxCB
from services import code_adaptive, coding_service, feature_service, sandbox, user_service
from states import SandboxStates
from utils import texts
from utils.telegram import safe_edit, typing

router = Router(name="sandbox")


async def _show_task(message, state: FSMContext, task, *, lead: str | None = None) -> None:
    """Enter the coding state for `task` and render its card (optionally with a lead)."""
    await state.set_state(SandboxStates.coding)
    await state.update_data(task_id=task.id, attempts=0)
    text = texts.sandbox_adaptive_card(task, lead) if lead else texts.sandbox_task_card(task)
    await safe_edit(message, text, inline.sandbox_task(task.topic))


@router.callback_query(MenuCB.filter(F.action == "sandbox"))
async def open_sandbox(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await safe_edit(query.message, texts.sandbox_intro(), inline.sandbox_categories())
    await query.answer()


@router.callback_query(SandboxCB.filter(F.action == "cat"))
async def open_category(query: CallbackQuery, callback_data: SandboxCB, state: FSMContext) -> None:
    await state.clear()
    user = await user_service.get_user(query.from_user.id)
    solved = await models.get_solved_task_ids(query.from_user.id)
    topic = callback_data.topic
    await safe_edit(
        query.message,
        texts.sandbox_topic_intro(topic),
        inline.sandbox_topic_tasks(topic, feature_service.is_pro(user), solved),
    )
    await query.answer()


@router.callback_query(SandboxCB.filter(F.action == "adaptive"))
async def open_adaptive(query: CallbackQuery, state: FSMContext) -> None:
    pick = await code_adaptive.pick(query.from_user.id)
    if pick is None:
        await query.answer("Пока нет доступных задач 🤔", show_alert=True)
        return
    # pick() already respects the free/PRO gate, so no extra check is needed.
    await _show_task(query.message, state, pick.task, lead=pick.reason)
    await query.answer()


@router.callback_query(SandboxCB.filter(F.action == "task"))
async def open_task(query: CallbackQuery, callback_data: SandboxCB, state: FSMContext) -> None:
    task = coding_service.get_task(callback_data.task_id)
    if task is None:
        await query.answer()
        return
    user = await user_service.get_user(query.from_user.id)
    if task.tier == "pro" and not feature_service.is_pro(user):
        await safe_edit(query.message, texts.upsell("🧪 Эта задача доступна в PRO."), inline.upsell())
        await query.answer(texts.PRO_LOCKED_ALERT, show_alert=True)
        return
    await _show_task(query.message, state, task)
    await query.answer()


@router.message(SandboxStates.coding, F.text & ~F.text.startswith("/"))
async def submit_solution(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    task_id, attempts = data.get("task_id"), int(data.get("attempts", 0))
    if not task_id:
        await state.clear()
        return

    allowed, _used, limit = await feature_service.practice_quota(message.from_user.id)
    if not allowed:
        await state.clear()
        await message.answer(texts.practice_limit_reached(limit), reply_markup=inline.upsell())
        return

    await typing(message.bot, message.chat.id, 0.5)
    outcome = await coding_service.submit(message.from_user.id, task_id, message.text or "", attempts)
    if outcome is None:
        await state.clear()
        await message.answer("Задача не найдена 🤔", reply_markup=inline.back_to_menu())
        return

    if outcome.passed:
        await feature_service.consume_practice(message.from_user.id)
        await state.clear()
        await message.answer(texts.sandbox_pass(outcome), reply_markup=inline.sandbox_done(outcome.task.topic))
    else:
        await state.update_data(attempts=attempts + 1)
        await message.answer(texts.sandbox_fail(outcome), reply_markup=inline.sandbox_task(outcome.task.topic))


@router.callback_query(MenuCB.filter(F.action == "debug"))
async def open_debug(query: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SandboxStates.debugging)
    await safe_edit(query.message, texts.debug_intro(), inline.debug_done())
    await query.answer()


@router.message(SandboxStates.debugging, F.text & ~F.text.startswith("/"))
async def explain_bug(message: Message, state: FSMContext) -> None:
    await state.clear()
    await typing(message.bot, message.chat.id, 0.5)
    result = await sandbox.run(message.text or "")
    await message.answer(texts.debug_result(result), reply_markup=inline.debug_done())
