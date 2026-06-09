"""Pytest bootstrap.

Configures a throwaway test database and a dummy token *before* any app module
is imported (config is a singleton evaluated at import time), then creates the
schema once. Tests use unique user ids to stay isolated on the shared DB.
"""
from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path

_TMP = Path(tempfile.gettempdir()) / "academy_pytest.db"

# Must precede the first `from config import ...` anywhere in the app.
os.environ["BOT_TOKEN"] = "123456:TEST_TOKEN_FOR_PYTEST"
os.environ["DB_PATH"] = str(_TMP)
os.environ["ADMIN_IDS"] = "1"
os.environ["PRO_IDS"] = ""

for _leftover in (_TMP, _TMP.with_name(_TMP.name + "-wal"), _TMP.with_name(_TMP.name + "-shm")):
    try:
        _leftover.unlink()
    except FileNotFoundError:
        pass

from database.db import init_db  # noqa: E402  (after env is set)

asyncio.run(init_db())
