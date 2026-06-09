"""FSM states for the Code Runner sandbox and Debug mode."""
from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class SandboxStates(StatesGroup):
    coding = State()     # awaiting a solution for a coding task
    debugging = State()  # awaiting broken code to explain
