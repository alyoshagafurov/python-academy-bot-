"""Subprocess harness that executes untrusted user code under hard limits.

Run as a separate process (never imported by the app). Reads a JSON job from
stdin, executes the code with a restricted builtins whitelist + OS resource
limits, runs the task's tests, and prints a JSON result to stdout.

Defense layers (combined with the parent AST screen in services/sandbox.py):
  • fresh interpreter, isolated namespace (user code can't see this module)
  • restricted __builtins__ (no __import__/open/eval/exec/...)
  • RLIMIT_CPU + RLIMIT_AS (where supported)
  • wall-clock timeout + SIGKILL enforced by the parent
"""
from __future__ import annotations

import contextlib
import io
import json
import sys

# Whitelisted builtins available to user code (safe, education-friendly).
_SAFE_NAMES = [
    "abs", "all", "any", "bool", "dict", "divmod", "enumerate", "filter",
    "float", "format", "int", "len", "list", "map", "max", "min", "print",
    "range", "repr", "reversed", "round", "set", "sorted", "str", "sum",
    "tuple", "zip", "ord", "chr",
    # exceptions so user code can raise/except normally
    "Exception", "ValueError", "TypeError", "IndexError", "KeyError",
    "ZeroDivisionError", "StopIteration", "RuntimeError", "ArithmeticError",
]


def _safe_builtins() -> dict:
    import builtins
    return {name: getattr(builtins, name) for name in _SAFE_NAMES if hasattr(builtins, name)}


def _apply_limits() -> None:
    """Best-effort OS resource limits (each is skipped if the platform refuses)."""
    try:
        import resource
    except Exception:
        return

    def _set(name: str, soft: int, hard: int) -> None:
        res = getattr(resource, name, None)
        if res is None:
            return
        try:
            resource.setrlimit(res, (soft, hard))
        except (ValueError, OSError):
            pass  # not enforceable on this platform (e.g. macOS)

    _MB = 1024 * 1024
    _set("RLIMIT_CPU", 2, 3)                 # CPU seconds (runaway loops)
    _set("RLIMIT_AS", 256 * _MB, 256 * _MB)  # address space (memory bombs, Linux)
    _set("RLIMIT_FSIZE", 0, 0)               # no file writes at all
    _set("RLIMIT_NPROC", 0, 0)               # no new processes/threads (anti fork-bomb)


def _jsonable(value):
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return repr(value)[:200]


def main() -> None:
    _apply_limits()
    try:
        job = json.loads(sys.stdin.read() or "{}")
    except Exception:
        print(json.dumps({"status": "runtime_error", "error": "bad job"}))
        return

    code = job.get("code", "")
    func_name = job.get("func")
    tests = job.get("tests") or []

    namespace = {"__builtins__": _safe_builtins()}
    out = io.StringIO()
    result: dict = {"status": "passed"}

    try:
        with contextlib.redirect_stdout(out):
            exec(compile(code, "<user>", "exec"), namespace)

            if func_name:
                fn = namespace.get(func_name)
                if not callable(fn):
                    result = {"status": "no_function", "func": func_name}
                else:
                    passed = 0
                    for case in tests:
                        args, expected = case[0], case[1]
                        try:
                            got = fn(*args)
                        except Exception as exc:  # noqa: BLE001 — report any user error
                            result = {"status": "runtime_error",
                                      "error_type": type(exc).__name__,
                                      "error": str(exc)[:200], "args": _jsonable(args)}
                            break
                        if got != expected:
                            result = {"status": "failed", "args": _jsonable(args),
                                      "expected": _jsonable(expected), "got": _jsonable(got),
                                      "passed": passed, "total": len(tests)}
                            break
                        passed += 1
                    else:
                        result = {"status": "passed", "passed": passed, "total": len(tests)}
    except SyntaxError as exc:
        result = {"status": "syntax", "error": exc.msg, "line": exc.lineno or 1}
    except Exception as exc:  # noqa: BLE001
        result = {"status": "runtime_error", "error_type": type(exc).__name__, "error": str(exc)[:200]}

    result["stdout"] = out.getvalue()[:500]
    print(json.dumps(result, default=lambda o: repr(o)[:200]))


if __name__ == "__main__":
    main()
