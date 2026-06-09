"""Pure-logic unit tests: levels, AST code-check, feature gates."""
from __future__ import annotations

from database.models import User
from services import feature_service, level_service
from services.code_check import check


# ── Levels ─────────────────────────────────────────────────────────────────

def test_level_thresholds():
    assert level_service.level_info(0).level == 1
    assert level_service.level_info(120).level == 2
    assert level_service.level_info(260).level == 3


def test_levels_monotonic_and_bounded():
    previous = 0
    for xp in range(0, 3000, 25):
        info = level_service.level_info(xp)
        assert info.level >= previous
        assert 0 <= info.percent <= 100
        previous = info.level


# ── AST code-check ───────────────────────────────────────────────────────

def test_code_check_assign_string():
    assert check("name = 'Alex'", ("assigns_string:name",)).passed
    bad = check("name = 5", ("assigns_string:name",))
    assert not bad.passed and bad.syntax_ok


def test_code_check_strips_markdown():
    assert check("```python\nname = 'x'\n```", ("assigns_string:name",)).passed


def test_code_check_func_arity_and_return():
    assert check("def double(x):\n    return x * 2", ("defines_func:double:1", "returns")).passed


def test_code_check_loop_and_print():
    assert check("for i in range(3):\n    print(i)", ("has_for", "calls:print")).passed


def test_code_check_syntax_error_flagged():
    result = check("name = ", ("assigns:name",))
    assert not result.passed and not result.syntax_ok


# ── Feature gates ──────────────────────────────────────────────────────────

def _user(**overrides) -> User:
    base = dict(user_id=1, username="t", xp=0, current_lesson=1,
                selected_mode=None, registration_date="2026-01-01")
    base.update(overrides)
    return User(**base)


def test_is_pro_flag_and_none():
    assert feature_service.is_pro(None) is False
    assert feature_service.is_pro(_user()) is False
    assert feature_service.is_pro(_user(is_pro=1)) is True


def test_code_topic_gates():
    free = _user()
    assert feature_service.can_code_topic(free, "variables") is True
    assert feature_service.can_code_topic(free, "loops") is False
    assert feature_service.can_code_topic(_user(is_pro=1), "loops") is True


def test_hard_mode_gate():
    assert feature_service.can_hard_mode(_user()) is False
    assert feature_service.can_hard_mode(_user(is_pro=1)) is True
