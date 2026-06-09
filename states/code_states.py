"""FSM states for the Code Practice flow (waiting for a code submission)."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class CodeStates(StatesGroup):
    waiting = State()  # awaiting the user's code as a text message
