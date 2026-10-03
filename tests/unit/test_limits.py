"""Resource guards (limits.py + render.py + cli wiring)."""

from __future__ import annotations

import subprocess

import pytest
from conftest import run_calc

from calc.errors import LimitError
from calc.limits import (
    apply_digit_limit,
    check_comb,
    check_factorial,
    max_expression_chars,
    max_factorial_arg,
    max_result_digits,
    timeout_seconds,
)


def test_defaults() -> None:
    assert max_result_digits() == 100_000
    assert max_factorial_arg() == 20_000
    assert max_expression_chars() == 10_000
    assert timeout_seconds() == 10.0


def test_env_overrides(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CALC_MAX_FACTORIAL_ARG", "50")
    assert max_factorial_arg() == 50


def test_check_factorial_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CALC_MAX_FACTORIAL_ARG", "100")
    with pytest.raises(LimitError):
        check_factorial(101)


def test_check_comb_rejects(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CALC_MAX_COMB_N", "10")
    with pytest.raises(LimitError):
        check_comb(11, 5)


def test_apply_digit_limit_runs() -> None:
    # idempotent: raising the cap twice is fine
    apply_digit_limit()
    apply_digit_limit()


def test_render_overflow_is_limit_error() -> None:
    from calc import render as render_module

    # well above the effective str() threshold (the interpreter applies its
    # cap with a small linear-scan slack, so 2x margin is used)
    value = 10 ** (max_result_digits() * 2)
    with pytest.raises(LimitError):
        render_module.render(value, 4)


def test_eval_factorial_arg_guard() -> None:
    with pytest.raises(LimitError):
        # direct op-level call; CLI path asserted in contract tests
        from calc.ops.eval_ops import evaluate

        evaluate(f"factorial({max_factorial_arg() + 1})")


def test_cli_factorial_guard_fast() -> None:
    proc = run_calc("eval", "factorial(10**7)")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("LimitError: ")
    assert proc.stderr.count("\n") == 1


def test_cli_huge_exact_result_limit_error() -> None:
    proc = run_calc("eval", "2**10000000", "--exact")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("LimitError: ")


def test_cli_expression_length_guard() -> None:
    huge = "1+" * (max_expression_chars() // 2 + 5) + "1"
    proc = run_calc("eval", huge)
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("LimitError: ")


def test_cli_timeout_flag_bounds_sympy() -> None:
    """A pathological sympy integral returns a typed LimitError quickly."""
    proc = run_calc(
        "calculus",
        "integrate",
        "sin(x)*exp(x**3)*cos(x**2)",
        "--var",
        "x",
        "--timeout",
        "1",
    )
    # either finishes quickly with a symbolic answer, or a typed LimitError —
    # never a traceback and never a multi-minute hang
    assert proc.returncode in (0, 1)
    if proc.returncode == 1:
        assert proc.stderr.startswith("LimitError: ")
        assert proc.stderr.count("\n") == 1


def _run_with_env(args: list[str], **env: str) -> subprocess.CompletedProcess[str]:
    import os

    full = dict(os.environ)
    full.update(env)
    return subprocess.run(
        ["uv", "run", "calc", *args],
        capture_output=True,
        text=True,
        check=False,
        env=full,
        timeout=30,
    )


def test_env_timeout_disables_guard() -> None:
    proc = _run_with_env(
        ["eval", "2+2"],
        CALC_TIMEOUT_SECONDS="0",
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == "4"


def test_default_timeout_allows_normal_work() -> None:
    proc = run_calc("eval", "1+1")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "2"
