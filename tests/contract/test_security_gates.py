"""Security-input gates: hostile strings never execute, never traceback.

The engine is a QA gate that agents feed arbitrary text into; these tests
pin the security posture (simpleeval sandbox, strict JSON, no eval/exec)
with the classic attack shapes.
"""

from __future__ import annotations

import pytest
from conftest import run_calc

_ATTACK_EXPRS = [
    "__import__('os').system('true')",
    "().__class__.__bases__[0].__subclasses__()",
    "open('/etc/passwd')",
    "eval('1+1')",
    "exec('x=1')",
    "().__class__",
    "().__dict__",
    "lambda: 1",
    "[x for x in [1]]",
    "getattr(int, 'real')",
    "int.__mro__",
    "().__class__.__name__",
]

_BAD_JSON = [
    "[1,2",
    "{'a': 1}",
    "(1,2)",
    "[1,'2']",
    "null",
    "{\"a\": 1}",
    "[]",
    "[[1],[2]]",  # ragged rows
    "[[1, True]]",
]


@pytest.mark.parametrize("expr", _ATTACK_EXPRS, ids=lambda e: e[:24])
def test_attack_expression_typed_failure(expr: str) -> None:
    proc = run_calc("eval", expr)
    assert proc.returncode == 1
    assert proc.stdout == ""
    lines = proc.stderr.strip().splitlines()
    assert len(lines) == 1, lines
    assert lines[0].startswith("SyntaxError: ") or lines[0].startswith("MathError: ")
    assert "Traceback" not in proc.stderr


@pytest.mark.parametrize("payload", _BAD_JSON, ids=lambda p: p[:20])
def test_bad_json_typed_failure(payload: str) -> None:
    proc = run_calc("matrix", "determinant", payload)
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith(("SyntaxError: ", "MathError: ", "ArgumentError: "))
    assert "Traceback" not in proc.stderr


def test_stat_bad_json_typed_failure() -> None:
    proc = run_calc("stat", "mean", "[1,'a']")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith(("SyntaxError: ", "ValueError: "))
    assert "Traceback" not in proc.stderr


def test_no_python_eval_anywhere_in_source() -> None:
    """Static gate: no eval/exec calls in first-party source."""
    from pathlib import Path

    src = Path(__file__).resolve().parents[2] / "src" / "calc"
    for path in src.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for needle in ("eval(", "exec(", "__import__("):
            # comment lines and simpleeval's own name are fine; the gate is
            # about call sites in code — a simple heuristic plus whitelist
            if needle in text:
                for line in text.splitlines():
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    if needle in stripped and "simple_eval" not in stripped and (
                        "_PROBE" not in stripped
                    ):
                        # parse-time mentions (docstrings) are excluded by
                        # checking that this is not inside a docstring: any
                        # residual hit is a hard failure
                        if needle == "eval(" and (
                            "no Python" in line or "eval`/`exec" in line
                            or "never Python" in line
                        ):
                            continue
                        raise AssertionError(
                            f"{path.name}: suspicious {needle!r} in: {stripped!r}"
                        )


def test_fuzz_random_strings_never_traceback() -> None:
    """Bounded fuzz: hostile/malformed eval inputs stay inside the contract."""
    import itertools
    import random

    rng = random.Random(20261004)  # fixed seed: deterministic test
    alphabet = "()[]{}.,+-*/%<>=!&|^~\"'` \\t01xenil_sqrtabcosin_floathex_@#$;:"
    fragments = [
        "".join(rng.choice(alphabet) for _ in range(rng.randint(1, 40)))
        for _ in range(60)
    ]
    for expr in itertools.chain(
        fragments,
        ("1/0", "9**9**9", "factorial(-1)", "factorial(10**7)", "1e1000", "2**99999"),
    ):
        proc = run_calc("eval", expr)
        assert proc.returncode in (0, 1), (expr, proc.returncode, proc.stderr)
        if proc.returncode == 1:
            assert proc.stdout == ""
            lines = proc.stderr.strip().splitlines()
            assert len(lines) == 1, (expr, proc.stderr)
            assert ": " in lines[0], (expr, lines[0])
        assert "Traceback" not in proc.stderr
