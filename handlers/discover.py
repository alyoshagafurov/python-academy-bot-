"""Discovery: theory search, favourites and smart recommendations."""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import inline
from keyboards.callbacks import MenuCB
from services import bookmark_service, recommend_service, search_service, user_service
from states import SearchStates
from utils import texts
from utils.telegram import safe_edit

router = Router(name="discover")


# ───────────────────────────────── Search ─────────────────────────────────

@router.callback_query(MenuCB.filter(F.action == "search"))
async def open_search(query: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SearchStates.querying)
    await safe_edit(query.message, texts.search_prompt(), inline.back_to_menu())
    await query.answer()


@router.message(SearchStates.querying, F.text & ~F.text.startswith("/"))
async def run_search(message: Message, state: FSMContext) -> None:
    await state.clear()
    query = message.text or ""
    hits = search_service.search(query)
    await message.answer(texts.search_results(query, hits), reply_markup=inline.search_results(hits))


@router.message(Command("search"))
async def cmd_search(message: Message, state: FSMContext) -> None:
    tg = message.from_user
    await user_service.register_user(tg.id, tg.username or tg.full_name)
    await state.set_state(SearchStates.querying)
    await message.answer(texts.search_prompt(), reply_markup=inline.back_to_menu())


# ──────────────────────────────── Favourites ──────────────────────────────

@router.callback_query(MenuCB.filter(F.action == "favorites"))
async def open_favorites(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    items = await bookmark_service.list_lessons(query.from_user.id)
    await safe_edit(query.message, texts.bookmarks_list(items), inline.bookmarks(items))
    await query.answer()


@router.message(Command("favorites"))
async def cmd_favorites(message: Message, state: FSMContext) -> None:
    await state.clear()
    tg = message.from_user
    await user_service.register_user(tg.id, tg.username or tg.full_name)
    items = await bookmark_service.list_lessons(tg.id)
    await message.answer(texts.bookmarks_list(items), reply_markup=inline.bookmarks(items))


# ────────────────────────────── Recommendations ───────────────────────────

@router.callback_query(MenuCB.filter(F.action == "recommend"))
async def open_recommend(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    recs = await recommend_service.recommend(query.from_user.id)
    await safe_edit(query.message, texts.recommendations(recs), inline.recommendations(recs))
    await query.answer()
