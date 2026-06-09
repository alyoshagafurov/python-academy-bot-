"""FSM state for free-text theory search."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class SearchStates(StatesGroup):
    querying = State()  # awaiting a search query from the user
