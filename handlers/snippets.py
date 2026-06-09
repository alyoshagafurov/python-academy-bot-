"""Code library: ready-to-copy Minecraft + Python scripts.

A read-only reference (no XP, no locks): пять категорий → список скриптов →
карточка с кодом, который копируется в VS Code и сразу работает в Minecraft.
"""
from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards import inline
from keyboards.callbacks import SnippetCB
from lessons import snippets as all_snippets
from utils import texts
from utils.telegram import safe_edit

router = Router(name="snippets")

# (cat_id, emoji, title) — display order of the library.
CATEGORIES: list[tuple[str, str, str]] = [
    ("buildings", "🏠", "Постройки"),
    ("effects", "✨", "Эффекты"),
    ("games", "🎮", "Мини-игры"),
    ("tools", "🛠", "Инструменты"),
    ("art", "🎨", "Пиксель-арт"),
]
_CAT = {cid: (emoji, title) for cid, emoji, title in CATEGORIES}


def _by_category(category: str):
    return [s for s in all_snippets() if s.category == category]


def _category_counts():
    return [(emoji, title, len(_by_category(cid))) for cid, emoji, title in CATEGORIES]


async def _show_home(message) -> None:
    await safe_edit(message, texts.snippets_intro(_category_counts()),
                    inline.snippet_categories(CATEGORIES))


@router.callback_query(SnippetCB.filter(F.action == "home"))
async def open_library(query: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await _show_home(query.message)
    await query.answer()


@router.callback_query(SnippetCB.filter(F.action == "cat"))
async def open_category(query: CallbackQuery, callback_data: SnippetCB) -> None:
    cat = callback_data.category
    if cat not in _CAT:
        await query.answer()
        return
    emoji, title = _CAT[cat]
    snips = _by_category(cat)
    await safe_edit(query.message, texts.snippet_list(emoji, title, snips),
                    inline.snippet_list_kb(cat, snips))
    await query.answer()


@router.callback_query(SnippetCB.filter(F.action == "view"))
async def open_snippet(query: CallbackQuery, callback_data: SnippetCB) -> None:
    snip = next((s for s in all_snippets() if s.id == callback_data.snippet_id), None)
    if snip is None:
        await query.answer()
        return
    await safe_edit(query.message, texts.snippet_card(snip),
                    inline.snippet_card_kb(snip.category))
    await query.answer()


@router.message(Command("codes"))
async def cmd_codes(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(texts.snippets_intro(_category_counts()),
                         reply_markup=inline.snippet_categories(CATEGORIES))
