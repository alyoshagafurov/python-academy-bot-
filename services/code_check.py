"""Safe validation of user-submitted Python via AST parsing — no execution.

A task declares a list of string "checks" (data-driven, JSON-friendly), e.g.
["assigns_string:name", "calls:print"]. We parse the submitted source into an
AST and verify each check structurally. Nothing is ever executed, so it's safe.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass, field

_MISSING = object()


@dataclass
class CheckResult:
    passed: bool
    syntax_ok: bool
    message: str                      # friendly feedback (first failure)
    failed: list[str] = field(default_factory=list)


def _clean(source: str) -> str:
    """Strip Markdown code fences / stray backticks users often paste."""
    text = source.strip()
    lines = text.splitlines()
    if lines and lines[0].lstrip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].rstrip().endswith("```"):
        lines = lines[:-1]
    return "\n".join(lines).strip().strip("`").strip()


class _Analyzer:
    """Collects structural facts about the code in a single AST walk."""

    def __init__(self, tree: ast.AST) -> None:
        self.assigns: dict[str, ast.AST | None] = {}
        self.calls: set[str] = set()
        self.funcs: dict[str, int] = {}
        self.loaded: set[str] = set()
        self.has_for = self.has_while = self.has_if = self.has_return = False

        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    self._record_target(target, node.value)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                self.assigns[node.target.id] = node.value
            elif isinstance(node, ast.Call):
                func = node.func
                if isinstance(func, ast.Name):
                    self.calls.add(func.id)
                elif isinstance(func, ast.Attribute):
                    self.calls.add(func.attr)
            elif isinstance(node, ast.FunctionDef):
                self.funcs[node.name] = len(node.args.args)
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                self.loaded.add(node.id)
            elif isinstance(node, ast.For):
                self.has_for = True
            elif isinstance(node, ast.While):
                self.has_while = True
            elif isinstance(node, ast.If):
                self.has_if = True
            elif isinstance(node, ast.Return):
                self.has_return = True

    def _record_target(self, target: ast.AST, value: ast.AST) -> None:
        if isinstance(target, ast.Name):
            self.assigns[target.id] = value
        elif isinstance(target, (ast.Tuple, ast.List)):
            for element in target.elts:
                if isinstance(element, ast.Name):
                    self.assigns[element.id] = None  # value unknown in unpacking


def _is_string(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, str)


def _is_int(node: ast.AST | None) -> bool:
    return isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool)


def _is_list(node: ast.AST | None) -> bool:
    return isinstance(node, ast.List)


def _eval_check(spec: str, an: _Analyzer) -> tuple[bool, str]:
    """Return (passed, failure_message) for a single check spec."""
    parts = spec.split(":")
    kind = parts[0]
    arg = parts[1] if len(parts) > 1 else None
    arg2 = parts[2] if len(parts) > 2 else None

    if kind == "assigns":
        return arg in an.assigns, f"Нужно создать переменную <b>{arg}</b>."
    if kind == "assigns_string":
        node = an.assigns.get(arg, _MISSING)
        return _is_string(node) if node is not _MISSING else False, \
            f"Переменная <b>{arg}</b> должна хранить строку (текст в кавычках)."
    if kind == "assigns_int":
        node = an.assigns.get(arg, _MISSING)
        return _is_int(node) if node is not _MISSING else False, \
            f"Переменная <b>{arg}</b> должна хранить число."
    if kind == "assigns_list":
        node = an.assigns.get(arg, _MISSING)
        return _is_list(node) if node is not _MISSING else False, \
            f"Переменная <b>{arg}</b> должна быть списком в квадратных скобках []."
    if kind == "calls":
        return arg in an.calls, f"Используй вызов <b>{arg}(...)</b>."
    if kind == "uses_name":
        return arg in an.loaded, f"Где-то используй переменную <b>{arg}</b> (например, выведи её)."
    if kind == "has_for":
        return an.has_for, "Добавь цикл <b>for</b>."
    if kind == "has_while":
        return an.has_while, "Добавь цикл <b>while</b>."
    if kind == "has_if":
        return an.has_if, "Добавь условие <b>if</b>."
    if kind == "returns":
        return an.has_return, "Функция должна возвращать значение через <b>return</b>."
    if kind == "defines_func":
        if arg not in an.funcs:
            return False, f"Определи функцию <b>{arg}</b> через <b>def</b>."
        if arg2 is not None and an.funcs[arg] != int(arg2):
            return False, f"У функции <b>{arg}</b> должно быть {arg2} аргумент(а)."
        return True, ""
    # Unknown check spec — treat as satisfied rather than blocking the user.
    return True, ""


def check(source: str, checks: tuple[str, ...]) -> CheckResult:
    """Validate `source` against a task's `checks`."""
    code = _clean(source)
    if not code:
        return CheckResult(False, True, "Кажется, ты не прислал код. Напиши его сообщением 🙂")

    try:
        tree = ast.parse(code)
    except SyntaxError as error:
        line = error.lineno or 1
        return CheckResult(
            False, False,
            f"⚠️ <b>Синтаксическая ошибка</b> (строка {line}): {error.msg}.\n"
            "Проверь скобки, кавычки и отступы.",
        )

    analyzer = _Analyzer(tree)
    failed: list[str] = []
    first_message = ""
    for spec in checks:
        ok, message = _eval_check(spec, analyzer)
        if not ok:
            failed.append(spec)
            first_message = first_message or message

    if failed:
        return CheckResult(False, True, first_message, failed)
    return CheckResult(True, True, "")
