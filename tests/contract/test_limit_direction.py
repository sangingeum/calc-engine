"""Limit-direction contract (CALC-04 follow-up): two-sided by default."""

from __future__ import annotations

import pytest
from conftest import run_calc


def test_two_sided_default_fails_on_jump() -> None:
    proc = run_calc("calculus", "limit", "1/x", "--var", "x", "--approach", "0")
    assert proc.returncode == 1
    assert proc.stdout == ""
    assert proc.stderr.startswith("MathError: limit does not exist"), proc.stderr
    assert "left=" in proc.stderr and "right=" in proc.stderr
    assert proc.stderr.count("\n") == 1


def test_right_hand_direction_opt_in() -> None:
    proc = run_calc(
        "calculus", "limit", "1/x", "--var", "x", "--approach", "0", "--dir", "+"
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == "inf"
    assert proc.stderr == ""


def test_left_hand_direction_opt_in() -> None:
    proc = run_calc(
        "calculus", "limit", "1/x", "--var", "x", "--approach", "0", "--dir", "-"
    )
    assert proc.returncode == 0
    assert proc.stdout.strip() == "-inf"


def test_agreeing_two_sided_limit_unchanged() -> None:
    proc = run_calc("calculus", "limit", "sin(x)/x", "--var", "x", "--approach", "0")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "1.0000"


def test_dir_rejected_for_other_ops() -> None:
    proc = run_calc("calculus", "derive", "x**2", "--var", "x", "--dir", "+")
    assert proc.returncode == 1
    assert proc.stderr.startswith("ArgumentError: --dir is only valid for limit")


def test_large_approach_two_sided_valid() -> None:
    # at a large finite approach point both sides agree: a valid result
    proc = run_calc("calculus", "limit", "x**2", "--var", "x", "--approach", "100")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "10000.0000"


@pytest.mark.parametrize(
    ("expr", "approach", "expected"),
    [
        ("abs(x)/x", "0", "MathError"),
        ("1/x", "0", "MathError"),
        ("sin(x)/x", "0", None),  # agreeing limit: exit 0
    ],
    ids=["abs-jump", "pole", "agreeing"],
)
def test_direction_matrix(expr: str, approach: str, expected: str | None) -> None:
    proc = run_calc("calculus", "limit", expr, "--var", "x", "--approach", approach)
    if expected is None:
        assert proc.returncode == 0
    else:
        assert proc.returncode == 1
        assert proc.stderr.startswith(f"{expected}: ")
