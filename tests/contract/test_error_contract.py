"""Error-contract edge cases: prefixes, security guarantees, exit codes."""

from __future__ import annotations

from conftest import run_calc


def test_error_prefixes_map_to_taxonomy() -> None:
    cases = [
        (["eval", "1/0"], "MathError"),
        (["eval", "open(1)"], "SyntaxError"),
        (["convert-unit", "1", "zzz", "m"], "ValueError"),
        (["calculus", "frobnicate", "x", "--var", "x"], "ArgumentError"),
    ]
    for args, prefix in cases:
        proc = run_calc(*args)
        assert proc.returncode == 1
        assert proc.stdout == ""
        assert proc.stderr.strip().startswith(f"{prefix}: "), proc.stderr


def test_eval_dunder_attribute_access_blocked() -> None:
    proc = run_calc("eval", "().__class__")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("SyntaxError: "), proc.stderr


def test_error_line_has_description_after_prefix() -> None:
    proc = run_calc("eval", "1/0")
    assert proc.stderr.startswith("MathError: ")
    assert len(proc.stderr.strip().split(":", 1)[1].strip()) > 0


def test_success_exit_code_zero() -> None:
    proc = run_calc("eval", "2+2")
    assert proc.returncode == 0


def test_precision_flag_global() -> None:
    two = run_calc("eval", "1/3", "--precision", "2")
    assert two.stdout.strip() == "0.33"
    six = run_calc("eval", "1/3", "--precision", "6")
    assert six.stdout.strip() == "0.333333"
