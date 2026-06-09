"""Safe sandboxed code execution + deterministic, explainable feedback.

A two-layer guard: an AST screen (this module) rejects imports / dunder access
/ dangerous names *before* running, then a locked-down subprocess
(services/_sandbox_runner.py) executes under resource limits and a wall-clock
timeout. No LLM, fully deterministic, scalable.

NOTE: This is a pragmatic education sandbox (layered, good enough to stop the
common escapes), not a hardened CTF jail. For very high-risk multitenancy,
move execution to a container/gVisor worker — the interface here stays the same.
"""
from __future__ import annotations

import ast
import asyncio
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path

_RUNNER = Path(__file__).resolve().parent / "_sandbox_runner.py"

# Reject pathologically large submissions before we even parse them.
_MAX_CODE_LEN = 20_000

# Names that must never be callable/referenced inside the sandbox.
_BLOCKED_NAMES = {
    "eval", "exec", "compile", "open", "__import__", "input", "globals",
    "locals", "vars", "getattr", "setattr", "delattr", "dir", "help",
    "exit", "quit", "breakpoint", "memoryview", "classmethod", "staticmethod",
}


@dataclass
class SandboxResult:
    status: str                  # passed|failed|runtime_error|syntax|blocked|timeout|no_function
    message: str = ""            # raw reason (for syntax/blocked/timeout)
    passed: int = 0
    total: int = 0
    args: object = None
    expected: object = None
    got: object = None
    error_type: str = ""
    error: str = ""
    line: int = 0
    func: str = ""
    stdout: str = ""

    @property
    def ok(self) -> bool:
        return self.status == "passed"


def _screen(code: str) -> tuple[bool, str, str]:
    """Static safety screen. Returns (ok, status, reason)."""
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return False, "syntax", f"строка {exc.lineno or 1}: {exc.msg}"

    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            return False, "blocked", "импорты в песочнице запрещены"
        if isinstance(node, ast.Attribute) and isinstance(node.attr, str) and node.attr.startswith("__"):
            return False, "blocked", "доступ к служебным __атрибутам запрещён"
        if isinstance(node, ast.Name) and node.id in _BLOCKED_NAMES:
            return False, "blocked", f"использование {node.id}() в песочнице запрещено"
    return True, "", ""


def _from_data(data: dict) -> SandboxResult:
    return SandboxResult(
        status=data.get("status", "runtime_error"),
        passed=int(data.get("passed", 0)),
        total=int(data.get("total", 0)),
        args=data.get("args"),
        expected=data.get("expected"),
        got=data.get("got"),
        error_type=data.get("error_type", ""),
        error=data.get("error", ""),
        line=int(data.get("line", 0)),
        func=data.get("func", ""),
        stdout=data.get("stdout", ""),
    )


async def run(code: str, func: str | None = None, tests: list | None = None,
              timeout: float = 4.0) -> SandboxResult:
    """Execute `code` safely; if `func`/`tests` given, grade against them."""
    if not code or not code.strip():
        return SandboxResult("blocked", "Пустой код — пришли решение.")
    if len(code) > _MAX_CODE_LEN:
        return SandboxResult("blocked", f"Слишком длинный код (> {_MAX_CODE_LEN} символов).")

    ok, status, reason = _screen(code)
    if not ok:
        return SandboxResult(status, reason)

    payload = json.dumps({"code": code, "func": func, "tests": tests or []})
    proc = await asyncio.create_subprocess_exec(
        sys.executable, str(_RUNNER),
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.DEVNULL,
    )
    try:
        out, _ = await asyncio.wait_for(proc.communicate(payload.encode()), timeout=timeout)
    except asyncio.TimeoutError:
        with _suppress():
            proc.kill()
        return SandboxResult("timeout", "Код выполнялся слишком долго — возможно, бесконечный цикл.")

    try:
        data = json.loads(out.decode() or "{}")
    except json.JSONDecodeError:
        return SandboxResult("runtime_error", error="Не удалось безопасно выполнить код.")
    return _from_data(data)


class _suppress:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return True


# ───────────────────────── deterministic feedback ─────────────────────────

_RUNTIME_HINTS = {
    "ZeroDivisionError": "Деление на ноль — проверь делитель.",
    "IndexError": "Выход за границы списка — индексы считаются с 0.",
    "KeyError": "Нет такого ключа в словаре.",
    "TypeError": "Несовместимые типы (например, число + строка).",
    "NameError": "Используешь необъявленную переменную.",
    "ValueError": "Некорректное значение для операции.",
}


def feedback(result: SandboxResult) -> str:
    """Explainable, beginner-friendly feedback for a result (HTML)."""
    s = result.status
    if s == "passed":
        return "✅ Все тесты пройдены!"
    if s == "syntax":
        return f"⚠️ <b>Синтаксис</b> ({result.message}).\nПроверь скобки, двоеточия и отступы."
    if s == "blocked":
        return f"🚫 {result.message}"
    if s == "timeout":
        return f"⏳ {result.message}"
    if s == "no_function":
        return f"Не нашёл функцию <b>{result.func}</b>. Объяви её через <code>def {result.func}(...)</code>."
    if s == "runtime_error":
        hint = _RUNTIME_HINTS.get(result.error_type, result.error or "ошибка выполнения")
        head = f"💥 <b>{result.error_type or 'Ошибка'}</b>: {hint}"
        return head
    if s == "failed":
        lines = [
            f"❌ Тест не прошёл.\nНа входе <code>{result.args}</code> "
            f"ожидалось <code>{result.expected}</code>, а вернулось <code>{result.got}</code>."
        ]
        if result.got is None:
            lines.append("Похоже, функция ничего не возвращает — добавь <b>return</b>.")
        elif result.passed > 0:
            lines.append("Ты очень близко — часть тестов уже зелёная. Проверь этот случай (часто это границы).")
        return "\n".join(lines)
    return "Не удалось разобрать результат."
