"""Backend Projects: portfolio-worthy, multi-step guided builds.

Flow: list → project card (preview, free for everyone) → step detail → mark
done (awards XP, advances) → next step → completion. PRO projects are fully
previewable; only *progressing* through their steps requires PRO.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import inline
from keyboards.callbacks import MenuCB, ProjectCB
from services import feature_service, project_service, user_service
from utils import texts
from utils.telegram import safe_edit

router = Router(name="projects")


def _locked(project, user) -> bool:
    return project.tier == "pro" and not feature_service.is_pro(user)


async def _render_menu(message, user_id: int, is_pro: bool) -> None:
    statuses = await project_service.overview(user_id)
    await safe_edit(message, texts.projects_intro(statuses), inline.projects_menu(statuses, is_pro))


@router.callback_query(MenuCB.filter(F.action == "projects"))
async def open_projects(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    user = await user_service.get_user(query.from_user.id)
    await _render_menu(query.message, query.from_user.id, feature_service.is_pro(user))
    await query.answer()


@router.callback_query(ProjectCB.filter(F.action == "open"))
async def open_project(query: CallbackQuery, callback_data: ProjectCB, state: FSMContext) -> None:
    await state.clear()
    project = project_service.get_project(callback_data.project_id)
    if project is None:
        await query.answer()
        return
    user = await user_service.get_user(query.from_user.id)
    status = await project_service.status(query.from_user.id, project)
    await safe_edit(query.message, texts.project_card(status), inline.project_card(status, feature_service.is_pro(user)))
    await query.answer()


@router.callback_query(ProjectCB.filter(F.action == "step"))
async def open_step(query: CallbackQuery, callback_data: ProjectCB, state: FSMContext) -> None:
    project = project_service.get_project(callback_data.project_id)
    if project is None:
        await query.answer()
        return
    user = await user_service.get_user(query.from_user.id)
    if _locked(project, user):
        await safe_edit(query.message, texts.upsell(f"{project.emoji} Проект «{project.title}» открывается в PRO."), inline.upsell())
        await query.answer(texts.PRO_LOCKED_ALERT, show_alert=True)
        return

    status = await project_service.status(query.from_user.id, project)
    if status.finished:
        await safe_edit(query.message, texts.project_card(status), inline.project_card(status, True))
        await query.answer("Проект уже завершён 🏆")
        return
    await safe_edit(query.message, texts.project_step(project, status.step), inline.project_step(project.id))
    await query.answer()


@router.callback_query(ProjectCB.filter(F.action == "done"))
async def complete_step(query: CallbackQuery, callback_data: ProjectCB, state: FSMContext) -> None:
    project = project_service.get_project(callback_data.project_id)
    if project is None:
        await query.answer()
        return
    user = await user_service.get_user(query.from_user.id)
    if _locked(project, user):
        await safe_edit(query.message, texts.upsell(f"{project.emoji} Проект «{project.title}» открывается в PRO."), inline.upsell())
        await query.answer(texts.PRO_LOCKED_ALERT, show_alert=True)
        return

    result = await project_service.advance(query.from_user.id, project.id)
    if result is None:
        await query.answer()
        return
    status = await project_service.status(query.from_user.id, project)
    await safe_edit(query.message, texts.project_step_result(result), inline.project_step_done(status))
    await query.answer("🏆 Шаг засчитан!" if result.completed else "")


@router.message(Command("projects"))
async def cmd_projects(message: Message, state: FSMContext) -> None:
    await state.clear()
    tg = message.from_user
    await user_service.register_user(tg.id, tg.username or tg.full_name)
    user = await user_service.get_user(tg.id)
    statuses = await project_service.overview(tg.id)
    await message.answer(
        texts.projects_intro(statuses),
        reply_markup=inline.projects_menu(statuses, feature_service.is_pro(user)),
    )
